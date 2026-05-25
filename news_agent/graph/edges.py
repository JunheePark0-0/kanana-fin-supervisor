def route_after_internal_check(state) -> str:
    if state.get("internal_ok"):
        return "to_external"
    if state.get("internal_attempt", 0) < 2:
        return "retry"
    return "to_external"


def route_after_finance(state) -> str:
    if state.get("has_finance_results"):
        return "has_results"
    if state.get("internal_context"):
        return "has_results"
    return "cannot_answer"


def route_after_final_check(state) -> str:
    route = state.get("final_check_route", "cannot_answer")
    final_attempt = state.get("final_attempt", 0)
    if route == "pass":
        return "pass"
    if final_attempt >= 2:
        return "cannot_answer"
    if route == "regenerate":
        return "regenerate"
    if route == "re_retrieve":
        return "re_retrieve"
    return "cannot_answer"
