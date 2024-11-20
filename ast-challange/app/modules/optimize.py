import ast
import base64
import traceback

import app.modules.optimizations as modules_optimizations


def optimizer(my_ast, verbose=True):
    """
    Главная функция оптимизации.
    """
    # Итоговый скор
    total_deobfuscation_score = 0
    # Цикл оптимизации
    is_loop_opted = True

    # Сброс счётчика вызовов базового трансформера
    modules_optimizations.BaseTransformer.calls = 0

    # Счётчик количества слоёв преобразования
    iter_num = 0
    MAX_ITERS = 4096

    # Получение всех доступных оптимизаторов
    optimizers = collect_optimizers()

    # Начальное состояние AST для сравнения
    before_dump = ast.dump(my_ast, indent=1)

    while is_loop_opted:
        if verbose:
            print(f"Iteration {iter_num}")
        iter_num += 1

        is_loop_opted = False

        for opt in optimizers:
            try:
                if verbose:
                    print(f"Processing: {opt.__name__}")

                if not opt.active:
                    if verbose:
                        print(f"Skipping inactive optimizer: {opt.__name__}")
                    continue

                opt_object: modules_optimizations.BaseTransformer = opt()
                opt_object.verbose = verbose

                # Применение трансформера
                opt_object.visit(my_ast)

                # Декодирование строк после каждого трансформера
                my_ast = decode_strings(my_ast)

                if opt_object.replace_flag:
                    # Считаем общий скор оптимизации
                    total_deobfuscation_score += (
                        opt_object.deobfuscation_score
                        * opt_object.number_of_replacements
                    )
                    is_loop_opted = True
                    if verbose:
                        print(
                            f"Applied! Operation score = {opt_object.deobfuscation_score}, "
                            f"Replacements = {opt_object.number_of_replacements}"
                        )

            except Exception as e:
                if verbose:
                    print(f"Failed optimizer: {opt.__name__}")
                    print(">>>")
                    traceback.print_exc()
                    print("<<<")

        # Проверяем, изменилось ли AST
        new_dump = ast.dump(my_ast, indent=1)
        if before_dump != new_dump:
            is_loop_opted = True
        before_dump = new_dump

        # Проверяем на превышение лимита итераций
        if iter_num > MAX_ITERS:
            print("Reached maximum iteration limit.")
            break

    if verbose:
        print("Optimization completed in", modules_optimizations.BaseTransformer.calls, "calls")

    # Исправление пропущенных местоположений
    my_ast = ast.fix_missing_locations(my_ast)

    return my_ast, total_deobfuscation_score


def collect_optimizers():
    """
    Собирает все подклассы BaseTransformer.
    """
    optimizers = set()
    temp = modules_optimizations.BaseTransformer.__subclasses__()
    new_temp = set()

    while temp:
        for new_opt in temp:
            if new_opt not in optimizers:
                optimizers.add(new_opt)
            new_opt_subcl = new_opt.__subclasses__()
            if new_opt_subcl:
                new_temp.update(new_opt_subcl)

        temp = new_temp
        new_temp = set()

    return optimizers


def decode_strings(ast_tree):
    """
    Декодирует все строки Base64 и применяет пользовательские лямбда-функции.
    """
    lambda_func = find_lambda_func(ast_tree)

    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Пробуем декодировать Base64
            try:
                decoded = base64.b64decode(node.value).decode("utf-8")
                node.value = decoded
            except Exception:
                pass

            # Применяем пользовательскую лямбда-функцию, если она есть
            if lambda_func:
                try:
                    node.value = lambda_func(node.value)
                except Exception as e:
                    if hasattr(ast_tree, 'verbose') and ast_tree.verbose:
                        print(f"Failed to apply lambda: {e}")

    return ast_tree


def find_lambda_func(ast_tree):
    """
    Находит и возвращает первую лямбда-функцию в AST, если она есть.
    """
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Lambda):
            try:
                lambda_code = compile(ast.Expression(node.value), filename="<string>", mode="eval")
                return eval(lambda_code)
            except Exception as e:
                if hasattr(ast_tree, 'verbose') and ast_tree.verbose:
                    print(f"Failed to compile lambda: {e}")
    return None
