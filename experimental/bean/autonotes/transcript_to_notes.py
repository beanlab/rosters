import sys
from pathlib import Path

from myteam.workflow import run_agent

this_folder = Path(__file__).parent


def main(instructions_file: Path, transcript_file: Path):
    results = run_agent(
        agent='pi',
        model='openai/gpt-5.5',
        prompt=instructions_file.read_text().format(
            transcript=transcript_file.read_text(),
            backlog_integration_instructions=(this_folder / 'basic-markdown-backlog-instructions.md').read_text(),
            header="# MyTeam weekly discussion"
        ),
        output={
            "notes": "Markdown of the meeting notes."
        }
    )
    (this_folder / 'output.md').write_text(results.output['notes'])
    # print(results.output['notes'])


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))
