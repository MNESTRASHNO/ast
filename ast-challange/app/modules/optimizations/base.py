import ast
import inspect


class BaseTransformer(ast.NodeTransformer):
    calls = 0
    max_calls = 10 ** 9
    depth_limit = 512_000
    deobfuscation_score = 10
    active = True
    verbose = False

    def __init__(self):
        super().__init__()
        self.replace_flag = False
        self.number_of_replacements = 0
        self.depth = 10

    def reset(self):
        self.calls = 0

    def visit(self, node):
        BaseTransformer.calls += 1
        self.depth += 1

        if self.depth > BaseTransformer.depth_limit:
            if self.verbose:
                print(f"Maximum recursion length reached! ({self.depth} software and {len(inspect.stack(0))} global)")
            return ast.Comment("AST: Reached maximum recursion")

        method = "visit_" + node.__class__.__name__
        if self.verbose:
            print(end="# ")
            print(">" * (self.depth), method)

        visitor = getattr(self, method, None)
        if visitor:
            new_node = visitor(node)
            if new_node != node and new_node is not None:
                self.replace_flag = True
                self.number_of_replacements += 1
                node = new_node

        try:
            node_cand = self.generic_visit(node)
            if node_cand is not None:
                node = node_cand
            if self.verbose:
                print(end="# ")
                print("<" * (self.depth), method)

            method = "leave_" + node.__class__.__name__
            visitor = getattr(self, method, None)
            if visitor:
                new_node = visitor(node)
                if new_node != node and new_node is not None:
                    self.replace_flag = True
                    self.number_of_replacements += 1
                    node = new_node
            if not visitor:
                node = self.generic_leave(node)
        except Exception:
            pass

        self.depth -= 1
        return node

    def generic_visit(self, node):
        for field, old_value in ast.iter_fields(node):
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, ast.AST) and not isinstance(value, (ast.Load, ast.Store)):
                        new_value = self.visit(value)
                        if new_value is not None:
                            value = new_value
                        if not isinstance(value, ast.AST):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, ast.AST) and not isinstance(old_value, (ast.Load, ast.Store)):
                new_node = self.visit(old_value)
                if new_node is None:
                    pass
                else:
                    setattr(node, field, new_node)
            elif isinstance(old_value, ast.Call) and isinstance(old_value.func, ast.Attribute):
                processed_node = self.process_replace_chain(old_value)
                if processed_node != old_value:
                    setattr(node, field, processed_node)
                    continue
            elif isinstance(old_value, ast.Lambda):
                processed_body = self.visit(old_value.body)
                if processed_body != old_value.body:
                    old_value.body = processed_body
                    self.replace_flag = True

                if isinstance(old_value.body, ast.Call):
                    processed_result = self.process_replace_chain(old_value.body)
                    if isinstance(processed_result, ast.Constant):
                        setattr(node, field, ast.Constant(processed_result.value))
                        continue

                evaluated_result = self.evaluate_lambda(old_value)
                if evaluated_result is not None:
                    setattr(node, field, ast.Constant(evaluated_result))
                    continue
        return node

    def process_replace_chain(self, node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            return node

        if node.func.attr == "replace" and isinstance(node.func.value, (ast.Constant, ast.Call)):
            original_string = None
            if isinstance(node.func.value, ast.Constant):
                original_string = node.func.value.value

            elif isinstance(node.func.value, ast.Call):
                processed_node = self.process_replace_chain(node.func.value)
                if isinstance(processed_node, ast.Constant):
                    original_string = processed_node.value

            if original_string is not None:
                current_node = node
                while isinstance(current_node, ast.Call) and current_node.func.attr == "replace":
                    args = current_node.args
                    if len(args) == 2 and all(isinstance(arg, ast.Constant) for arg in args):
                        original_string = original_string.replace(args[0].value, args[1].value)
                    else:
                        break
                    current_node = current_node.func.value if isinstance(current_node.func, ast.Attribute) else None
                return ast.Constant(original_string)

        return node




