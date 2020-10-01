from . import prompt_logic, prompts, aws_account_util


def start_tableau_server():
    region = prompt_logic.get_selected_region_or_prompt()
    answer = prompts.StartEC2Instance().ask(region)
    if answer == prompts.StartEC2Instance.NoStoppedInstances:
        ec2_count = aws_account_util.count_hammerhead_ec2_instances(region)
        print(f"Unable to stop instances, none of the {ec2_count} Hammerhead EC2 instances are stopped (tag:Pipeline = ProjectHammerhead)")
        prompt_logic.press_enter_to_continue()
    elif answer == prompts.CancelAnswer.title:
        print("User Cancelled")
    else:
        aws_account_util.start_instance(answer, region)
        prompt_logic.press_enter_to_continue()


def stop_tableau_server():
    region = prompt_logic.get_selected_region_or_prompt()
    answer = prompts.StopEC2Instance().ask(region)
    if answer == prompts.StopEC2Instance.NoStartedInstances:
        ec2_count = aws_account_util.count_hammerhead_ec2_instances(region)
        print(f"Unable to stop instances, none of the {ec2_count} Hammerhead EC2 instances are running (tag:Pipeline = ProjectHammerhead)")
        prompt_logic.press_enter_to_continue()
    elif answer == prompts.CancelAnswer.title:
        print("User Cancelled")
    else:
        aws_account_util.stop_instance(answer, region)
        prompt_logic.press_enter_to_continue()


def reboot_tableau_server():
    region = prompt_logic.get_selected_region_or_prompt()
    answer = prompts.RebootEC2Instance().ask(region)
    if answer == prompts.RebootEC2Instance.NoInstances:
        ec2_count = aws_account_util.count_hammerhead_ec2_instances(region)
        print(f"Unable to reboot instances, none of the {ec2_count} Hammerhead EC2 instances are running (tag:Pipeline = ProjectHammerhead)")
        prompt_logic.press_enter_to_continue()
    elif answer == prompts.CancelAnswer.title:
        print("User Cancelled")
    else:
        aws_account_util.reboot_instance(answer, region)
        prompt_logic.press_enter_to_continue()


def terminate_tableau_server():
    # TODO: unlicense Tableau Server before terminating
    region = prompt_logic.get_selected_region_or_prompt()
    answer = prompts.TerminateEC2Instance().ask(region)
    if answer == prompts.TerminateEC2Instance.NoInstances:
        print("Unable to terminate instances, No EC2 instances created by Hammerhead")
        prompt_logic.press_enter_to_continue()
    elif answer == prompts.CancelAnswer.title:
        print("user Cancelled")
    else:
        if prompt_logic.type_to_continue("terminate"):
            aws_account_util.terminate_instance(answer, region)
        prompt_logic.press_enter_to_continue()
