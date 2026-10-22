from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar, Callable


class GoBack(BaseException):
    def __init__(self, to_step):
        self.to_step = to_step
        super().__init__(to_step)


class ControlFlow(dict):
    """
    Learns what steps exist by initial should_run queries
    Raises an exception to return to an earlier step
    """

    def __init__(self):
        super().__init__()
        self._first_pass = True
        self._steps: dict[str, bool] = {}

    def first_pass(self) -> bool:
        return self._first_pass

    def should_run(self, step_name: str) -> bool:
        should = self._steps.get(step_name, True)
        self._steps[step_name] = False
        return should

    def __call__(self, step_name: str) -> bool:
        return self.should_run(step_name)
    
    def return_to(self, step_name: str):
        if step_name not in self._steps:
            raise ValueError(f'Unrecognized step: {step_name}')
        raise GoBack(step_name)

    def __bool__(self):
        return not self._steps or any(self._steps.values())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        should_run = False
        if exc_type is GoBack:
            self._first_pass = False
            for step in self._steps:
                if step == exc_val.to_step:
                    should_run = True
                self._steps[step] = should_run
            return True  # i.e. swallow the exception
        return False  # i.e. allow the exception to continue to raise


P = ParamSpec("P")
R = TypeVar("R")


def with_control(func: Callable[Concatenate[ControlFlow, P], R]):
    @wraps(func)
    def new_func(*args: P.args, **kwargs: P.kwargs) -> R:
        control = ControlFlow()
        # noinspection PyInconsistentReturns
        # ControlFlow will always be truthy on the first pass
        # And ControlFlow will always be truthy if the function should run again
        # And ControlFlow will always be falsy if func did not complete
        #  so the only way out is for func to complete
        while control:
            with control:
                return func(control, *args, **kwargs)

    return new_func


@with_control
def main(control: ControlFlow):
    if control.first_pass():
        control['count'] = 0

    if control('plan'):
        control['count'] += 1
        print('PLAN', control['count'])

    if control('build'):
        print('BUILD')

    if control('review'):
        decision = 'bad_idea' if control['count'] < 2 else 'great'
        print('REVIEW', decision)
        if decision == 'bad_idea':
            control.return_to('plan')

    if control('wrap-up'):
        print('WRAP UP')


if __name__ == '__main__':
    main()
