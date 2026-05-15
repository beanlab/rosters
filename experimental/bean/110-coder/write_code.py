from pathlib import Path

from myteam.workflow import run_agent
from myteam.workflow.models import StepResult

# AGENT = 'pi'
AGENT = 'codex'

ERRORS_DESCRIPTION = (
    "if this task cannot be accomplished (e.g. the file doesn't exist)"
    "set unfillable outputs to null and explain the problem here; "
    "otherwise set this to null"
)


def raise_on_error(results: StepResult):
    if errors := results.output['errors']:
        raise RuntimeError(errors)


def find_code_file(instructions: str) -> Path:
    results = run_agent(
        agent=AGENT,
        prompt=f"""
        What follows below is a coding task that references
        a file that needs to be implemented.
        
        Your task is to identify the code file that needs to be implemented,
        verify that it exists, and return the absolute path to it.
        
        -----
        {instructions}
        -----
        """,
        output={
            "filepath": "absolute path to the file to implement",
            "errors": ERRORS_DESCRIPTION
        }
    )

    raise_on_error(results)

    return Path(results.output['filepath'])


def stub_main(instructions: str, file: Path) -> list[str]:
    results = run_agent(
        agent=AGENT,
        prompt=f"""
            Please add this code to the file {file}:
            
            ```py
            def main():
                pass
                
            
            if __name__ == '__main__':
                main()
            ```

            If any of this code is superseded by existing code, keep the existing code.
            """,
        output={
            "comments": "a brief description of the edits made",
            "errors": ERRORS_DESCRIPTION
        }
    )

    raise_on_error(results)

    results = run_agent(
        agent=AGENT,
        prompt=f"""
            Your task is to establish the signature of `main`.
            
            `main` should reflect the commandline arguments of the program.
            
            For example, if the commandline usage expects a string and an integer:
            
            ```
            python myscript.py tacos 7
            ```
            
            then `main` would be defined:
            
            ```py
            def main(food: str, quantity: int):
                pass
            ```

            Then, in the `if __name__ == '__main__':` block,
            perform simple routing of inputs from `sys.argv` to `main`'s arguments, e.g.
            
            ```py
            if __name__ == '__main__':
                main(sys.argv[1], int(sys.argv[2]))
            ```
            
            Read through the following instructions to determine the required
            signature for `main`, update the code with this signature,
            and call `main` using the inputs in `sys.argv`.
            
            **Do not implement main**. Simply update it's signature and invocation.
            
            If not changes are needed (i.e. the program has no arguments), 
            simply note this and return.
            -----
            {instructions}
            -----
            """,
        output={
            "arguments": "a simple description of the arguments to `main` (name, type, and meaning)",
            "errors": ERRORS_DESCRIPTION
        }
    )

    raise_on_error(results)

    return ['main']


def implement_function(file: Path, instructions: str, next_function: str) -> list[str]:
    results = run_agent(
        agent=AGENT,
        prompt=f"""
                You are part of a large team implementing a simple program
                described below.
                
                The program is contained in {file}.
                
                Your task is to implement **just** the function `{next_function}`.
                
                You are to use a distinct style:
                the function should read like pseudo-code, with a clear self-documenting
                style. A reader should be able to look at the code, read it out loud,
                and understand the intent and logical flow of the function.
                
                For example, a function that needs to query the user for a list of items and
                then print that list of items might look like:
                
                ```py
                def query_and_display_items(how_many: int):
                    items = query_items(how_many)
                    display_items(items)
                ```
                
                A function is a simple wiring diagram of the logic of the function.
                
                When naming functions, choose a name that is simple and accurate,
                but not overly verbose or specific to the implementation.
                Consider multiple names that could be used for a function,
                and select the one that is most simple while still being descriptive.
                
                Now, some functions are **so** simple, they shouldn't be decomposed further.
                For example, a single loop to display the items:
                
                ```py
                def display_items(items: list[str]):
                    for item in items:
                        print('-', item)
                ```
                
                When thinking through the implementation of a function,
                you need to decide whether to decompose into additional functions
                or simply implement the needed logic. Consider multiple possibilities,
                then pick the approach that strikes the best balance between
                the single-responsibility-principle and excessive decomposition.
                
                Only decompose a function when doing so meaningfully reduces complexity.
                
                As you implement a function, you will likely need to reference
                new functions. Include function stubs for these functions,
                **but do not implement them**.

                For example, if you had just implemented `query_and_display_items`
                in the example above, you would also include:
                
                ```py
                def query_items(how_many: int) -> list[str]:
                    pass
                    
                    
                def display_items(items: list[str]):
                    pass
                ```
                
                Define new functions above their call site.
                
                Avoid side effects across function boundaries
                except where necessary.
                
                Always include type hints.
                
                These functions will be implemented at a later step.
                
                -----
                {instructions}
                -----
                """,
        output={
            "function_logic": "the high-level steps of the function you implemented",
            "new_functions": ["a list of the names of functions you added"],
            "errors": ERRORS_DESCRIPTION
        }
    )

    raise_on_error(results)

    if not isinstance(results.output['new_functions'], list):
        raise ValueError(results)

    return results.output['new_functions']


def main(instructions: str):
    file = find_code_file(instructions)

    unfilled_functions = stub_main(instructions, file)
    while unfilled_functions:
        next_function = unfilled_functions.pop()
        unfilled_functions.extend(implement_function(file, instructions, next_function))

    # tests = find_tests(file)
    # while test_results := run_tests():
    #     fix_code(test_results)


if __name__ == '__main__':
    # task_instructions = sys.stdin.read()
    task_instructions = """
    ## 👩🏻‍🎨 Fruit Salad
    
    Write a program that:
    
    1. Asks the user for a series of fruit
      - The user inputs `''` (empty string) when they are done
    2. Print the list of fruits with a `"~"` bullet in front of each fruit.

    Put the code in scratch/fruit_salad.py
    """
    
    task_instructions = """
    ## 🎣 `fishing.py`

    Write a program that allows the user to input information on a series of catches.
    
    For each catch, the user should provide the place, type, and size (in inches) of the fish.
    
    Then allow the user to specify which types of fish to report on.
    For each type specified, print a report indicating:
    
    - the total number of fish of that type
    - the average size of fish of that type (rounded to 1 decimal place)
    - the catch with the largest fish of that type
    
    ```
    Place: Utah Lake
    Type of fish: Trout
    Size (inches): 6
    Place: Lake Powell
    Type of fish: Bass
    Size (inches): 12
    Place: Flaming Gorge
    Type of fish: Bass
    Size (inches): 18
    Place: Strawberry
    Type of fish: Trout
    Size (inches): 13
    Place: Bear Lake
    Type of fish: Trout
    Size (inches): 15
    Place: 
    What types of fish do you want to report on?
    Type: Bass
    Type: Trout
    Type: 
    Total # of Bass: 2
    Average size for Bass: 15.0
    Best Bass catch: 18.0 inches at Flaming Gorge
    Total # of Trout: 3
    Average size for Trout: 11.3
    Best Trout catch: 15.0 inches at Bear Lake
    ```
    
    Implement this in scratch/fishing.py
    """
    
    task_instructions = """
    ## 🧑🏽‍🍳 `recipe.py`

    Write a program that allows the user to input a list of ingredients.
    
    For each ingredient, they should provide the item, the quantity, and the units (e.g. cups, tsps, etc.)
    
    Then query the user for the scaling factor (how much do they want to scale the recipe).
    
    Then print out the recipe scaled by that factor. Round to 1 decimal place.

    ```
    What ingredients are in your recipe?
    Ingredient: flour
    Quantity: 2
    Unit: cups
    Ingredient: salt
    Quantity: 1
    Unit: tbs
    Ingredient: baking soda
    Quantity: 1
    Unit: tsps
    Ingredient: water
    Quantity: 1
    Unit: cups
    Ingredient: 
    Scaling factor: 2.5
    New Recipe:
      5.0 (cups) flour
      2.5 (tbs) salt
      2.5 (tsps) baking soda
      2.5 (cups) water
    ```
    
    Implement in scratch/recipe.py
    """
    main(task_instructions)
