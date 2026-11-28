from decimal import Decimal, ROUND_HALF_UP


RULE_VERSION = "1.0.0"

MIN_RATING = 1
MAX_RATING = 5
GAP_THRESHOLD = 3

RELEVANCE_WEIGHTS = {
    1: 1,
    2: 2,
    3: 3,
}

RELEVANCE_LABELS = {
    1: "Low",
    2: "Medium",
    3: "High",
}

READINESS_NEEDS_STRENGTHENING = "Needs strengthening"
READINESS_DEVELOPING = "Developing readiness"
READINESS_HIGHER = "Higher readiness"
READINESS_INSUFFICIENT = "Insufficient information"
READINESS_UNAVAILABLE = "Analysis unavailable"

DISCLAIMER = (
    "These results are based on student self-assessment "
    "and defined academic relationships. They are advisory "
    "and do not establish actual competence, predict grades, "
    "or determine enrollment eligibility."
)


def validate_rating(rating):

    if (
        type(rating) is not int
        or not MIN_RATING <= rating <= MAX_RATING
    ):
        raise ValueError(
            "Self-rating must be an integer from 1 to 5."
        )

    return rating


def relevance_weight(relevance):

    if (
        type(relevance) is not int
        or relevance not in RELEVANCE_WEIGHTS
    ):
        raise ValueError(
            "Relevance must be an integer from 1 to 3."
        )

    return RELEVANCE_WEIGHTS[relevance]


def is_competency_gap(rating):

    validate_rating(rating)

    return rating <= GAP_THRESHOLD


def gap_description(rating):

    validate_rating(rating)

    descriptions = {
        1: "Needs significant strengthening",
        2: "Needs strengthening",
        3: "Further practice recommended",
        4: "Self-reported independent ability",
        5: "Self-reported ability to explain",
    }

    return descriptions[rating]


def weighted_readiness(items):

    items = list(items)

    if not items:
        return None

    numerator = 0
    denominator = 0
    missing = False

    for rating, relevance in items:

        weight = relevance_weight(relevance)

        if rating is None:
            missing = True
            continue

        validate_rating(rating)

        numerator += rating * weight
        denominator += weight

    if missing:
        return None

    return Decimal(numerator) / Decimal(denominator)


def classify_readiness(score, has_impacts=True):

    if not has_impacts:
        return READINESS_UNAVAILABLE

    if score is None:
        return READINESS_INSUFFICIENT

    score = Decimal(str(score))

    if (
        not score.is_finite()
        or not Decimal("1") <= score <= Decimal("5")
    ):
        raise ValueError(
            "Readiness score must be between 1 and 5."
        )

    if score < Decimal("3"):
        return READINESS_NEEDS_STRENGTHENING

    if score < Decimal("4"):
        return READINESS_DEVELOPING

    return READINESS_HIGHER


def display_score(score):

    if score is None:
        return None

    return Decimal(str(score)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def priority_score(rating, relevance):

    validate_rating(rating)

    weight = relevance_weight(relevance)

    if not is_competency_gap(rating):
        return 0

    return (MAX_RATING - rating) * weight


def recommendation_text(competency_name, subject_name):

    return (
        f"Review and practice {competency_name} "
        f"as preparation for {subject_name}."
    )