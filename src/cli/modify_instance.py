from . import prompt_logic, prompts, aws_account_util


def start_tableau_server():
    region = prompt_logic.get_selected_region_or_prompt()
    answer = prompts.StartEC2Instance().ask(region)
    if answer == prompts.StartEC2Instance.NoStoppedInstances:
        print("Unable to start instances, No EC2 instances are stopped")
        prompt_logic.press_enter_to_continue()
    elif answer == prompts.CancelAnswer:
        print("User Cancelled")
    else:
        instance_id = answer.split(" ")[0]
        aws_account_util.start_instance(instance_id)
        prompt_logic.press_enter_to_continue()


def stop_tableau_server():
    region = prompt_logic.get_selected_region_or_prompt()
    answer = prompts.StopEC2Instance().ask(region)
    if answer == prompts.StopEC2Instance.NoStartedInstances:
        print("Unable to stop instances, No EC2 instances are started")
        prompt_logic.press_enter_to_continue()
    elif answer == prompts.CancelAnswer:
        print("User Cancelled")
    else:
        instance_id = answer.split(" ")[0]
        aws_account_util.stop_instance(instance_id)
        prompt_logic.press_enter_to_continue()


def reboot_tableau_server():
    region = prompt_logic.get_selected_region_or_prompt()
    answer = prompts.RebootEC2Instance().ask(region)
    if answer == prompts.RebootEC2Instance.NoInstances:
        print("Unable to reboot instances, No EC2 instances are started")
        prompt_logic.press_enter_to_continue()
    elif answer == prompts.CancelAnswer:
        print("User Cancelled")
    else:
        aws_account_util.reboot_instance(answer)
        prompt_logic.press_enter_to_continue()


def terminate_tableau_server():
    # TODO: unlicense Tableau Server before terminating
    region = prompt_logic.get_selected_region_or_prompt()
    answer = prompts.TerminateEC2Instance().ask(region)
    if answer == prompts.TerminateEC2Instance.NoInstances:
        print("Unable to terminate instances, No EC2 instances created by Hammerhead")
        prompt_logic.press_enter_to_continue()
    elif answer == prompts.CancelAnswer:
        print("user Cancelled")
    else:
        instance_id = answer.split(" ")[0]
        if prompt_logic.type_to_continue("terminate"):
            aws_account_util.terminate_instance(instance_id, region)
        prompt_logic.press_enter_to_continue()
