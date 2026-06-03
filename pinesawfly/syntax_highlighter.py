from __future__ import annotations

import html
import re
from functools import lru_cache
from pathlib import Path

from tree_sitter import Language, Node, Parser

import tree_sitter_go
import tree_sitter_java
import tree_sitter_lua
import tree_sitter_php
import tree_sitter_python

SUPPORTED_AST_LANGUAGES = {
    ".php": "php",
    ".py": "python",
    ".java": "java",
    ".lua": "lua",
    ".go": "go",
}

PHP_BUILTINS = {
    "echo", "print", "isset", "empty", "unset", "include", "include_once", "require", "require_once",
    "strlen", "strpos", "str_replace", "preg_match", "preg_replace", "count", "array_map",
    "array_filter", "array_merge", "json_encode", "json_decode", "htmlspecialchars", "intval",
    "floatval", "boolval", "trim", "explode", "implode", "in_array", "file_get_contents",
    "file_put_contents", "fopen", "fclose", "curl_exec", "header", "session_start",
}
PHP_SUPERGLOBALS = {"_SERVER", "_GET", "_POST", "_FILES", "_REQUEST", "_SESSION", "_ENV", "_COOKIE", "GLOBALS"}
MAGIC_METHODS = {"__construct", "__destruct", "__call", "__callStatic", "__get", "__set", "__isset", "__unset", "__sleep", "__wakeup", "__serialize", "__unserialize", "__toString", "__invoke", "__set_state", "__clone", "__debugInfo"}
MAGIC_CONSTANTS = {"__FILE__", "__LINE__", "__DIR__", "__FUNCTION__", "__CLASS__", "__TRAIT__", "__METHOD__", "__NAMESPACE__"}

KEYWORDS = {
    "php": {
        "control": {"if", "else", "elseif", "for", "foreach", "while", "switch", "case", "break", "continue", "return", "throw", "try", "catch", "finally", "default", "do", "match", "as"},
        "declaration": {"function", "class", "trait", "interface", "namespace", "use", "const", "fn"},
        "modifier": {"public", "private", "protected", "static", "final", "abstract", "readonly"},
        "type": {"int", "string", "bool", "boolean", "float", "double", "array", "object", "callable", "iterable", "void", "mixed", "never", "null", "true", "false", "self", "parent"},
        "operator": {"new", "instanceof", "and", "or", "xor"},
    },
    "python": {
        "control": {"if", "elif", "else", "for", "while", "break", "continue", "return", "raise", "try", "except", "finally", "with", "match", "case", "yield"},
        "declaration": {"class", "def", "lambda", "import", "from", "as", "global", "nonlocal"},
        "modifier": {"async", "await"},
        "type": {"None", "True", "False"},
        "operator": {"and", "or", "not", "is", "in"},
    },
    "java": {
        "control": {"if", "else", "for", "while", "do", "switch", "case", "break", "continue", "return", "throw", "try", "catch", "finally", "default", "yield"},
        "declaration": {"class", "interface", "enum", "record", "package", "import", "new", "extends", "implements"},
        "modifier": {"public", "private", "protected", "static", "final", "abstract", "native", "synchronized", "transient", "volatile", "strictfp"},
        "type": {"boolean", "byte", "char", "double", "float", "int", "long", "short", "void", "var", "null", "true", "false", "this", "super"},
        "operator": {"instanceof"},
    },
    "lua": {
        "control": {"if", "then", "else", "elseif", "for", "while", "repeat", "until", "break", "return", "do", "end", "in"},
        "declaration": {"function", "local"},
        "modifier": set(),
        "type": {"nil", "true", "false", "self"},
        "operator": {"and", "or", "not"},
    },
    "go": {
        "control": {"if", "else", "for", "range", "switch", "case", "default", "break", "continue", "return", "defer", "go", "select", "fallthrough"},
        "declaration": {"package", "import", "func", "type", "const", "var", "struct", "interface"},
        "modifier": set(),
        "type": {"bool", "byte", "complex64", "complex128", "error", "float32", "float64", "int", "int8", "int16", "int32", "int64", "rune", "string", "uint", "uint8", "uint16", "uint32", "uint64", "uintptr", "nil", "true", "false"},
        "operator": {"new", "make"},
    },
}

SCOPE_STYLES = {
    "comment": "color:#6A9955;",
    "keyword.control": "color:#569CD6;font-weight:600;",
    "keyword.declaration": "color:#569CD6;font-weight:600;",
    "storage.modifier": "color:#569CD6;font-weight:600;",
    "storage.type": "color:#4EC9B0;",
    "constant.language": "color:#4FC1FF;font-weight:600;",
    "variable": "color:#9CDCFE;",
    "variable.declaration": "color:#9CDCFE;font-weight:600;",
    "variable.other.php": "color:#9CDCFE;",
    "variable.other.superglobal": "color:#9CDCFE;font-weight:600;",
    "property": "color:#9CDCFE;",
    "function": "color:#DCDCAA;",
    "support.function": "color:#DCDCAA;",
    "entity.name.function": "color:#DCDCAA;font-weight:600;",
    "function.builtin": "color:#DCDCAA;font-weight:600;",
    "function.magic": "color:#DCDCAA;font-style:italic;font-weight:600;",
    "method": "color:#DCDCAA;",
    "method.declaration": "color:#DCDCAA;font-weight:600;",
    "class": "color:#4EC9B0;font-weight:600;",
    "entity.name.type.class": "color:#4EC9B0;font-weight:600;",
    "type": "color:#4EC9B0;",
    "namespace": "color:#4EC9B0;",
    "string": "color:#CE9178;",
    "constant.character.escape": "color:#DCDCAA;font-weight:600;",
    "constant.numeric": "color:#B5CEA8;",
    "operator": "color:#D4D4D4;",
    "punctuation": "color:#D4D4D4;",
    "punctuation.accessor": "color:#D4D4D4;",
    "punctuation.definition.tag": "color:#569CD6;",
    "tag": "color:#800000;font-weight:600;",
    "attribute": "color:#FF0000;",
    "css.property": "color:#0000FF;",
    "css.selector": "color:#800000;font-weight:600;",
    "js.keyword": "color:#0000FF;font-weight:600;",
    "js.function": "color:#DCDCAA;",
}

HTML_BLOCK = re.compile(r"(?is)<(?P<name>script|style)\b[^>]*>.*?</(?P=name)\s*>")
HTML_TOKEN = re.compile(r"(?P<comment><!--[\s\S]*?-->)|(?P<tag></?[A-Za-z][A-Za-z0-9:-]*|/?>)|(?P<string>\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*')|(?P<attr>\b[A-Za-z_:][-A-Za-z0-9_:.]*(?=\s*=))|(?P<number>\b\d+(?:\.\d+)?\b)")
CSS_TOKEN = re.compile(r"(?P<comment>/\*[\s\S]*?\*/)|(?P<string>\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*')|(?P<number>\b\d+(?:\.\d+)?(?:px|em|rem|vh|vw|%)?\b)|(?P<keyword>\b(?:color|background|display|position|grid|flex|margin|padding|border|width|height|font|font-family|font-size|line-height|transform|transition|animation|opacity|z-index)\b)|(?P<selector>[.#]?[A-Za-z_-][A-Za-z0-9_-]*(?=\s*\{))|(?P<operator>[{}:;,>+~])", re.IGNORECASE)
JS_TOKEN = re.compile(r"(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)|(?P<string>`(?:\\.|[^`])*`|\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*')|(?P<number>\b(?:0x[0-9A-Fa-f]+|\d+(?:\.\d+)?)\b)|(?P<keyword>\b(?:async|await|break|case|catch|class|const|continue|debugger|default|delete|do|else|export|extends|finally|for|from|function|get|if|import|in|instanceof|let|new|null|of|return|set|static|super|switch|this|throw|true|try|typeof|undefined|var|void|while|with|yield)\b)|(?P<function>\b[A-Za-z_$][A-Za-z0-9_$]*(?=\s*\())|(?P<operator>[+\-*/%=!&|?:.<>]+)|(?P<punct>[(){}\[\];,])")


def highlight_code(content: str, file_path: str) -> str:
    extension = Path(file_path).suffix.lower()
    language = SUPPORTED_AST_LANGUAGES.get(extension)
    if language == "php":
        return highlight_php_document(content)
    if language:
        return highlight_ast(content, language)
    if extension in {".html", ".htm"}:
        return highlight_html(content)
    if extension == ".css":
        return highlight_regex(content, CSS_TOKEN, css_scope)
    if extension in {".js", ".ts"}:
        return highlight_regex(content, JS_TOKEN, js_scope)
    return preserve(content)


def preserve(value: str) -> str:
    return html.escape(value).replace(" ", "&nbsp;").replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;").replace("\n", "<br>")


def emit(value: str, scope: str | None = None) -> str:
    escaped = preserve(value)
    if not scope:
        return escaped
    return f'<span style="{SCOPE_STYLES.get(scope, "color:#49454F;")}">{escaped}</span>'


@lru_cache(maxsize=None)
def parser_for(language: str) -> Parser:
    factories = {
        "php": tree_sitter_php.language_php,
        "php_only": tree_sitter_php.language_php_only,
        "python": tree_sitter_python.language,
        "java": tree_sitter_java.language,
        "lua": tree_sitter_lua.language,
        "go": tree_sitter_go.language,
    }
    return Parser(Language(factories[language]()))


def highlight_php_document(content: str) -> str:
    tag_pattern = re.compile(r"<\?(?:php|=)?|\?>", re.IGNORECASE)
    if not tag_pattern.search(content):
        return highlight_ast(content, "php_only")
    pieces: list[str] = []
    position = 0
    in_php = False
    for match in tag_pattern.finditer(content):
        if match.start() > position:
            chunk = content[position:match.start()]
            pieces.append(highlight_ast(chunk, "php_only") if in_php else highlight_html(chunk))
        pieces.append(emit(match.group(0), "punctuation.definition.tag"))
        in_php = not match.group(0).startswith("?>")
        position = match.end()
    if position < len(content):
        pieces.append(highlight_ast(content[position:], "php_only") if in_php else highlight_html(content[position:]))
    return "".join(pieces)


def highlight_ast(content: str, language: str) -> str:
    source = content.encode("utf-8")
    tree = parser_for(language).parse(source)
    spans: list[tuple[int, int, str]] = []
    collect_spans(tree.root_node, source, language, spans)
    return render_spans(source, spans)


def collect_spans(node: Node, source: bytes, language: str, spans: list[tuple[int, int, str]]) -> None:
    scope = scope_for_node(node, source, language)
    if scope and node.start_byte < node.end_byte and (not node.children or node.type in {"comment", "line_comment", "block_comment", "string_content", "heredoc_start", "heredoc_end", "escape_sequence"}):
        spans.append((node.start_byte, node.end_byte, scope))
        return
    for child in node.children:
        collect_spans(child, source, language, spans)


def render_spans(source: bytes, spans: list[tuple[int, int, str]]) -> str:
    spans = sorted(spans, key=lambda item: (item[0], -(item[1] - item[0])))
    pieces: list[str] = []
    position = 0
    for start, end, scope in spans:
        if start < position:
            continue
        if start > position:
            pieces.append(preserve(source[position:start].decode("utf-8", "replace")))
        pieces.append(emit(source[start:end].decode("utf-8", "replace"), scope))
        position = end
    if position < len(source):
        pieces.append(preserve(source[position:].decode("utf-8", "replace")))
    return "".join(pieces)


def scope_for_node(node: Node, source: bytes, language: str) -> str | None:
    scope_language = "php" if language == "php_only" else language
    text = node_text(node, source)
    if not text:
        return None
    if node.type in {"comment", "line_comment", "block_comment"}:
        return "comment"
    if node.type in {"escape_sequence", "escape"}:
        return "constant.character.escape"
    if is_string_node(node):
        return "string"
    if is_number_node(node):
        return "constant.numeric"
    if node.type == "php_tag":
        return "punctuation.definition.tag"
    if text in {"->", "::"}:
        return "punctuation.accessor"
    if node.type in {"+", "-", "*", "/", "%", "=", "==", "===", "!=", "!==", "<", ">", "<=", ">=", "&&", "||", "!", "=>", "??", ".."}:
        return "operator"
    if text in {"(", ")", "{", "}", "[", "]", ";", ",", "$", "\\", "<?php", "<?", "?>", ":", "."}:
        return "punctuation"
    keyword_scope = scope_for_keyword(text, scope_language)
    if keyword_scope:
        return keyword_scope
    if scope_language == "php":
        return scope_php_node(node, source, text)
    if scope_language == "python":
        return scope_python_node(node, text)
    if scope_language == "java":
        return scope_java_node(node, text)
    if scope_language == "lua":
        return scope_lua_node(node, text)
    if scope_language == "go":
        return scope_go_node(node, text)
    return None


def scope_for_keyword(text: str, language: str) -> str | None:
    groups = KEYWORDS.get(language)
    if not groups:
        return None
    if text in groups["control"]:
        return "keyword.control"
    if text in groups["declaration"]:
        return "keyword.declaration"
    if text in groups["modifier"]:
        return "storage.modifier"
    if text in groups["type"]:
        return "storage.type"
    if text in groups["operator"]:
        return "operator"
    return None


def scope_php_node(node: Node, source: bytes, text: str) -> str | None:
    parent = node.parent
    field = field_name(node)
    lowered = text.lower().lstrip("\\")
    if text in MAGIC_CONSTANTS:
        return "constant.language"
    if node.type in {"heredoc_start", "heredoc_end", "string_content"}:
        return "string"
    if node.type == "name":
        if parent and parent.type in {"class_declaration", "interface_declaration", "trait_declaration"} and field == "name":
            return "entity.name.type.class"
        if parent and parent.type in {"method_declaration", "function_definition"} and field == "name":
            return "function.magic" if text in MAGIC_METHODS else "entity.name.function"
        if parent and parent.type in {"function_call_expression", "scoped_call_expression"} and field in {"function", "name"}:
            return "function.builtin" if lowered in PHP_BUILTINS else "support.function"
        if parent and parent.type == "member_call_expression" and field == "name":
            return "support.function"
        if parent and parent.type in {"object_creation_expression", "qualified_name", "namespace_name", "namespace_use_clause"}:
            return "namespace" if has_ancestor(node, {"namespace_definition", "namespace_use_declaration"}) else "entity.name.type.class"
        if parent and parent.type == "variable_name":
            return "variable.other.superglobal" if text in PHP_SUPERGLOBALS else "variable.other.php"
        if parent and parent.type == "dynamic_variable_name":
            return "variable.other.php"
    if node.type == "variable_name":
        return "variable.other.superglobal" if text.lstrip("$") in PHP_SUPERGLOBALS else "variable.other.php"
    if node.type in {"namespace_name", "qualified_name"}:
        return "namespace"
    return None


def scope_python_node(node: Node, text: str) -> str | None:
    parent = node.parent
    field = field_name(node)
    if node.type == "identifier":
        if parent and parent.type == "class_definition" and field == "name":
            return "class"
        if parent and parent.type == "function_definition" and field == "name":
            return "entity.name.function"
        if parent and parent.type == "call" and field == "function":
            return "support.function"
        if parent and parent.type == "attribute" and field == "attribute":
            return "property"
        if has_ancestor(node, {"parameters", "typed_parameter", "default_parameter"}):
            return "variable.declaration"
        return "variable"
    return None


def scope_java_node(node: Node, text: str) -> str | None:
    parent = node.parent
    field = field_name(node)
    if node.type in {"type_identifier", "scoped_type_identifier"}:
        return "class"
    if node.type == "identifier":
        if parent and parent.type in {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"} and field == "name":
            return "class"
        if parent and parent.type in {"method_declaration", "constructor_declaration"} and field == "name":
            return "entity.name.function"
        if parent and parent.type == "method_invocation" and field == "name":
            return "support.function"
        if parent and parent.type in {"variable_declarator", "formal_parameter"} and field == "name":
            return "variable.declaration"
        return "variable"
    return None


def scope_lua_node(node: Node, text: str) -> str | None:
    parent = node.parent
    field = field_name(node)
    if node.type == "identifier":
        if parent and parent.type in {"function_declaration", "function_definition"} and field in {"name", "method"}:
            return "entity.name.function"
        if parent and parent.type == "method_index_expression" and field == "method":
            return "entity.name.function"
        if parent and parent.type == "function_call" and field == "name":
            return "support.function"
        if parent and parent.type in {"parameters", "variable_list"}:
            return "variable.declaration"
        return "variable"
    return None


def scope_go_node(node: Node, text: str) -> str | None:
    parent = node.parent
    field = field_name(node)
    if node.type == "type_identifier":
        return "class"
    if node.type == "package_identifier":
        return "namespace"
    if node.type == "field_identifier":
        return "entity.name.function" if parent and parent.type == "method_declaration" and field == "name" else "property"
    if node.type == "identifier":
        if parent and parent.type in {"function_declaration", "method_declaration"} and field == "name":
            return "entity.name.function"
        if parent and parent.type == "call_expression" and field == "function":
            return "support.function"
        if parent and parent.type in {"parameter_declaration", "short_var_declaration", "var_spec"} and field == "name":
            return "variable.declaration"
        return "variable"
    return None


def is_string_node(node: Node) -> bool:
    return node.type in {"string", "string_literal", "raw_string_literal", "interpreted_string_literal", "character_literal", "string_content", "heredoc_body", "heredoc_start", "heredoc_end", "nowdoc_string", "template_string"}


def is_number_node(node: Node) -> bool:
    return node.type in {"integer", "float", "integer_literal", "decimal_integer_literal", "hex_integer_literal", "octal_integer_literal", "binary_integer_literal", "floating_point_literal", "float_literal"} or "number" in node.type


def field_name(node: Node) -> str | None:
    parent = node.parent
    if not parent:
        return None
    for index, child in enumerate(parent.children):
        if child.id == node.id:
            return parent.field_name_for_child(index)
    return None


def has_ancestor(node: Node, types: set[str]) -> bool:
    parent = node.parent
    while parent:
        if parent.type in types:
            return True
        parent = parent.parent
    return False


def node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", "replace")


def highlight_html(content: str) -> str:
    pieces: list[str] = []
    position = 0
    for match in HTML_BLOCK.finditer(content):
        if match.start() > position:
            pieces.append(highlight_regex(content[position:match.start()], HTML_TOKEN, html_scope))
        block = match.group(0)
        open_end = block.find(">") + 1
        close_start = block.lower().rfind("</")
        pieces.append(highlight_regex(block[:open_end], HTML_TOKEN, html_scope))
        inner = block[open_end:close_start]
        pieces.append(highlight_regex(inner, JS_TOKEN, js_scope) if match.group("name").lower() == "script" else highlight_regex(inner, CSS_TOKEN, css_scope))
        pieces.append(highlight_regex(block[close_start:], HTML_TOKEN, html_scope))
        position = match.end()
    if position < len(content):
        pieces.append(highlight_regex(content[position:], HTML_TOKEN, html_scope))
    return "".join(pieces)


def highlight_regex(content: str, pattern: re.Pattern[str], scope_for_match) -> str:
    pieces: list[str] = []
    position = 0
    for match in pattern.finditer(content):
        if match.start() > position:
            pieces.append(preserve(content[position:match.start()]))
        pieces.append(emit(match.group(0), scope_for_match(match)))
        position = match.end()
    if position < len(content):
        pieces.append(preserve(content[position:]))
    return "".join(pieces)


def html_scope(match: re.Match[str]) -> str:
    return {"comment": "comment", "tag": "tag", "attr": "attribute", "string": "string", "number": "constant.numeric"}.get(match.lastgroup or "", "punctuation")


def css_scope(match: re.Match[str]) -> str:
    return {"comment": "comment", "string": "string", "number": "constant.numeric", "selector": "css.selector", "operator": "punctuation"}.get(match.lastgroup or "", "css.property")


def js_scope(match: re.Match[str]) -> str:
    return {"comment": "comment", "string": "string", "number": "constant.numeric", "function": "js.function", "operator": "operator", "punct": "operator"}.get(match.lastgroup or "", "js.keyword")
