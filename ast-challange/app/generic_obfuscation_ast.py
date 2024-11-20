import ast
import enum
import os
import sys
import threading
import time

import app.ast_comments as ast_lib
import app.modules.optimize as modules_optimize

sys.setrecursionlimit(1_000_000)
threading.stack_size(200_000_000)


class DebfuscationStatus(enum.Enum):
    SOURCE_PARSE_FAILED = "Error to parse source file"
    RESULT_PARSE_FAILED = "Error to parse deobfuscated ast"
    NOTHING_CHANGED = "No changes"
    DEOBFUSCATED = "Deobfuscated"
    DEOBFUSCATED_MINOR = "Changed, but cannot be count as obfuscation"


def deob(source, verbose=True):
    t = time.time()
    try:
        ast = ast_lib.parse(source=source, filename="<unknown>", type_comments=True)
        ast = intercept_exec_eval(ast)

    except Exception:
        return "", "", None, None, DebfuscationStatus.SOURCE_PARSE_FAILED
    unparse_before = ast_lib.unparse(ast)
    ast_before = ast_lib.dump(ast, indent=2)
    new_ast, deobfuscation_score = modules_optimize.optimizer(ast, verbose=verbose)
    ast_after = ast_lib.dump(new_ast, indent=2)
    try:
        unparse_after = ast_lib.unparse(new_ast)
    except Exception as e:
        if verbose:
            print(e)
        return (
            ast_before,
            ast_after,
            unparse_before,
            None,
            DebfuscationStatus.RESULT_PARSE_FAILED,
        )

    deobfuscation_status = DebfuscationStatus.NOTHING_CHANGED
    if deobfuscation_score >= 100:
        deobfuscation_status = DebfuscationStatus.DEOBFUSCATED
    elif unparse_before != unparse_after:
        deobfuscation_status = DebfuscationStatus.DEOBFUSCATED_MINOR

    if verbose:
        print("deobfuscation score", deobfuscation_score)
        print("time spent:", time.time() - t)

    return ast_before, ast_after, unparse_before, unparse_after, deobfuscation_status

def intercept_exec_eval(ast_tree):
    """
    Перехватывает и обрабатывает вызовы exec и eval.
    """
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
            if isinstance(node.args[0], ast.Constant):
                try:
                    decoded = compile(node.args[0].value, '<string>', 'exec')
                    print(f"Intercepted and compiled: {decoded}")
                except Exception as e:
                    print(f"Failed to compile exec/eval: {e}")
    return ast_tree

def unpack(source, verbose=False):
    ast_before, ast_after, unparse_before, unparse_after, deobfuscation_status = deob(
        source, verbose
    )
    if deobfuscation_status in [DebfuscationStatus.DEOBFUSCATED]:
        return unparse_after


def usage():
    print(f"Usage: {os.path.basename(sys.argv[0])} python_code.py")


def main():
    if len(sys.argv) != 2:
        return usage()
    with open(sys.argv[1], "rb") as f:
        new_code = deob(f.read())
        print(new_code)


if __name__ == "__main__":
    main()
