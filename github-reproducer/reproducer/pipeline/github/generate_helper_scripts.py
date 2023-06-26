import importlib.resources
import os

import reproducer.resources as resources


def generate(helper_script_dir):
    evaluator_text = importlib.resources.read_text(resources, 'evaluate_expressions.py')

    destination = os.path.join(helper_script_dir, 'eval_expression')
    with open(destination, 'w') as f:
        f.write(evaluator_text)
