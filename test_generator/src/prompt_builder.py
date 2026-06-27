def build_zeroshot_prompt(method):
    """Zero-shot baseline prompt: focal method only, no context, no repair.

    The model sees the class name, signature, body and (if present) the Javadoc,
    and is asked once for a JUnit 5 test class. The Documentation block is dropped
    entirely when no Javadoc is available.
    """
    class_name      = method['class_name']
    method_name     = method['method_name']
    signature       = method.get('signature', '')
    body            = method.get('body', '')
    test_class_name = f"{class_name}_{method_name}_Test"
    package         = '.'.join(method['full_name'].split('.')[:-2])

    prompt = f"""Write a JUnit 5 test class for the following Java method.

Class:     {class_name}
Method:    {method_name}
Signature: {signature}

Method implementation:
{body}
"""

    if method.get('javadoc'):
        prompt += f"\nDocumentation:\n{method['javadoc']}\n"

    prompt += f"""
Requirements:
- Name the test class exactly {test_class_name}, in package {package}.
- Use JUnit 5 (org.junit.jupiter.api.*) and include every import the test needs.
- Write tests only for {method_name}.
- Output only the complete Java source inside a single ```java ... ``` code block, with no text outside it."""
    return prompt
