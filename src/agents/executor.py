def execute(state):
    return f"""
    Execute this plan:

    {state.plan}

    Original goal:
    {state.goal}
    """
