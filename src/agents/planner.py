def plan(state):
    return f"""
    Create a plan for achieving this goal:

    {state.goal}

    Previous feedback:
    {state.critique}
    """
