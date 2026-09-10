def critique(state):
    return f"""
    Critically evaluate this output:

    Goal:
    {state.goal}

    Output:
    {state.output}

    Identify what should be improved.
    """
