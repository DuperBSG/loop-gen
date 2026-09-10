def improve(state):
    return f"""
    Based on the following critique:

    {state.critique}

    Determine what should change in the next iteration.
    """
