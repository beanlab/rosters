from myteam.workflow import run_agent


def main():
    result = run_agent(
        agent='pi',
        prompt="""
        Your task is to help me conduct a feasibility assessment.
        
        Our goal is to understand our options for how
        we can approach a problem. Allow the user to lead the discussion.
        Begin by asking the user the task or feature they want to build.
        
        What architectures, frameworks, interfaces, designs, definitions,
        and 3rd-party tools should be considered?
        
        What are the pros and cons of each approach discussed?
        
        Keep your responses short. Ask questions one-at-a-time, allowing the 
        user to discuss each question as needed before providing an answer. 
        
        When the user requests to conclude the session, provide a summary
        of the conversation as instructed in the output.
        """,
        output={
            'confirmation': 'The text the user provided requesting the session conclude',
            'chosen_strategy': 'A thorough description of the chosen strategy or design',
            'alternates_considered': 'An overview of each alternate discussed by not selected, '
                                     'including information about why that option was not selected'
        }
    )
    for key, value in result.output.items():
        print(key.center(40, '-'))
        print(value)
        print()


if __name__ == '__main__':
    main()
