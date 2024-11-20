import base64
from app.modules.optimizations.base import BaseTransformer, ast


class GoodEncodingLibs(BaseTransformer):
    """
    Трансформер для работы с Base64, replace и лямбда-функциями.
    """

    def leave_Call(self, node: ast.Call):
        """
        Обрабатывает вызовы exec и цепочки replace.
        """
        # Проверяем вызов exec
        if isinstance(node.func, ast.Name) and node.func.id == "exec":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                inner_call = node.args[0]

                # Проверяем, что это вызов __PYO__0254
                if isinstance(inner_call.func, ast.Name) and inner_call.func.id == "__PYO__0254":
                    # Раскрываем аргументы __PYO__0254
                    if len(inner_call.args) == 1 and isinstance(inner_call.args[0], ast.Constant):
                        obfuscated_code = inner_call.args[0].value

                        # Применяем лямбда-функцию
                        lambda_func = self.get_lambda_function("__PYO__0254")
                        if lambda_func:
                            try:
                                deobfuscated_code = self.clean_redundant_replace(lambda_func(obfuscated_code))
                                node.args[0] = ast.Constant(deobfuscated_code)
                                self.replace_flag = True
                                if self.verbose:
                                    print(f"Deobfuscated exec: {obfuscated_code} -> {deobfuscated_code}")
                            except Exception as e:
                                if self.verbose:
                                    print(f"Failed to apply lambda to exec: {e}")
            return node

        # Обрабатываем Base64 или цепочку replace
        decoded_node = self.handle_base64(node)
        if decoded_node is not None:
            return decoded_node

        replace_result = self.process_replace_chain(node)
        if isinstance(replace_result, ast.Constant):
            return replace_result

        return node

    def handle_base64(self, node: ast.Call):
        """
        Распознаёт и обрабатывает вызовы base64.b64decode и подобных функций.
        """
        if not isinstance(node.func, (ast.Attribute, ast.Name)):
            return None

        module = None
        method = None

        if isinstance(node.func, ast.Attribute):
            if not isinstance(node.func.value, ast.Name):
                return None
            module = __import__(node.func.value.id)
            method = node.func.attr
        else:
            return None

        # Проверяем, что это вызов base64
        if "base64" not in module.__name__ or not method.startswith("b64"):
            return None

        func = getattr(module, method)

        # Пробуем декодировать аргументы
        try:
            if len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
                decoded = base64.b64decode(node.args[0].value).decode("utf-8")
                return ast.Constant(decoded)
        except Exception as e:
            if self.verbose:
                print(f"Failed to decode Base64 string: {e}")

        return None

    def process_replace_chain(self, node: ast.Call):
        """
        Собирает и выполняет цепочку вызовов replace на строках за одну итерацию.
        """
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            return node

        # Проверка, является ли текущий узел вызовом replace
        if node.func.attr == "replace" and isinstance(node.func.value, (ast.Constant, ast.Call)):
            original_string = None

            # Если это строка, сохраняем начальное значение
            if isinstance(node.func.value, ast.Constant):
                original_string = node.func.value.value

            # Если это вложенный вызов replace, обрабатываем его
            elif isinstance(node.func.value, ast.Call):
                processed_node = self.process_replace_chain(node.func.value)
                if isinstance(processed_node, ast.Constant):
                    original_string = processed_node.value

            # Выполняем замены из цепочки replace
            if original_string is not None:
                current_node = node
                while isinstance(current_node, ast.Call) and current_node.func.attr == "replace":
                    args = current_node.args
                    if len(args) == 2 and all(isinstance(arg, ast.Constant) for arg in args):
                        if args[0].value != args[1].value:  # Пропускаем лишние replace
                            original_string = original_string.replace(args[0].value, args[1].value)
                    current_node = current_node.func.value if isinstance(current_node.func, ast.Attribute) else None
                return ast.Constant(original_string)

        return node

    def leave_Lambda(self, node: ast.Lambda):
        """
        Обрабатывает лямбда-функции, пытаясь вычислить их результат.
        """
        # Обрабатываем тело лямбда-функции
        node.body = self.visit(node.body)

        # Если тело содержит replace, пробуем его развернуть
        if isinstance(node.body, ast.Call):
            processed_result = self.process_replace_chain(node.body)
            if isinstance(processed_result, ast.Constant):
                return ast.Constant(processed_result.value)

        return node

    def get_lambda_function(self, name):
        """
        Возвращает скомпилированную лямбда-функцию по её имени.
        """
        for node in ast.walk(self.root_node):
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
                if isinstance(node.value, ast.Lambda):
                    try:
                        lambda_code = compile(ast.Expression(node.value), filename="<string>", mode="eval")
                        return eval(lambda_code)
                    except Exception as e:
                        if self.verbose:
                            print(f"Failed to compile lambda {name}: {e}")
        return None

    def clean_redundant_replace(self, code):
        """
        Удаляет лишние вызовы replace из строки.
        """
        try:
            lines = code.split('.replace(')
            cleaned_lines = []
            for line in lines:
                if len(cleaned_lines) == 0:
                    cleaned_lines.append(line)
                elif ')' not in line or line.split(')')[0].split(',')[0].strip() != line.split(')')[0].split(',')[1].strip():
                    cleaned_lines.append('.replace(' + line)
            return ''.join(cleaned_lines)
        except Exception as e:
            if self.verbose:
                print(f"Failed to clean redundant replaces: {e}")
            return code
