"""Go form source data to final output."""
import utils
run_command("python source2raw-eat.py")
run_command("python source2raw-survey.py")
run_command("python eat_correlations.py")
