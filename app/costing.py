"""Trip cost arithmetic shared by the budget check, the itinerary prompt and
the trip snapshot, so every place prices a trip the same way."""

from app.schemas import (
    CostBreakdown,
    CostLine,
    FlightResult,
    HotelResult,
    Itinerary,
    TravelRequirements,
)


def nights(requirements: TravelRequirements) -> int:
    """A 3 day trip needs 2 nights; a day trip still prices one night."""

    return max((requirements.duration_days or 1) - 1, 1)


def _matches(choice: str | None, name: str) -> bool:
    if not choice:
        return False

    choice, name = choice.casefold().strip(), name.casefold().strip()
    return choice == name or choice in name or name in choice


def pick_flight(
    flights: list[FlightResult], choice: str | None = None
) -> FlightResult | None:
    """The itinerary's chosen flight, else the cheapest one."""

    chosen = [flight for flight in flights if _matches(choice, flight.airline)]
    candidates = chosen or flights
    return min(candidates, key=lambda flight: flight.price) if candidates else None


def pick_hotel(
    hotels: list[HotelResult], choice: str | None = None
) -> HotelResult | None:
    """The itinerary's chosen hotel, else the cheapest one."""

    chosen = [hotel for hotel in hotels if _matches(choice, hotel.name)]
    candidates = chosen or hotels
    return min(candidates, key=lambda hotel: hotel.price_per_night) if candidates else None


def stay_cost(
    requirements: TravelRequirements,
    flight: FlightResult | None,
    hotel: HotelResult | None,
) -> tuple[float, float]:
    """Return (flights for everyone, hotel for every night)."""

    travelers = requirements.travelers or 1
    flight_cost = flight.price * travelers if flight else 0.0
    hotel_cost = hotel.price_per_night * nights(requirements) if hotel else 0.0
    return flight_cost, hotel_cost


def estimate_trip_cost(
    requirements: TravelRequirements,
    flights: list[FlightResult],
    hotels: list[HotelResult],
    itinerary: Itinerary | None,
) -> CostBreakdown:
    """Price the recommended flight and hotel plus the planned daily spend."""

    currency = requirements.budget_currency or "INR"
    notes: list[str] = []
    lines: list[CostLine] = []

    choice = itinerary.flight_choice if itinerary else None
    flight = None if requirements.flights_booked else pick_flight(flights, choice)

    choice = itinerary.hotel_choice if itinerary else None
    hotel = None if requirements.accommodation_booked else pick_hotel(hotels, choice)

    # Prices in another currency cannot be added up with the budget.
    priced = {"flight": flight, "hotel": hotel}

    for label, item in priced.items():
        if item is not None and item.currency != currency:
            notes.append(
                f"The {label} is priced in {item.currency}, not {currency}; "
                "it is left out of the total."
            )
            priced[label] = None

    flight, hotel = priced["flight"], priced["hotel"]

    flight_cost, hotel_cost = stay_cost(requirements, flight, hotel)
    travelers = requirements.travelers or 1

    if requirements.flights_booked:
        notes.append("Flights are already booked and not counted.")
    elif flight:
        trip = "round trip" if flight.round_trip else "one way"
        lines.append(
            CostLine(
                label="Flights",
                amount=flight_cost,
                detail=f"{flight.airline}, {flight.price:,.0f} × {travelers} ({trip})",
            )
        )
    elif not flights:
        notes.append("No flight prices were found.")

    if requirements.accommodation_booked:
        notes.append("Accommodation is already booked and not counted.")
    elif hotel:
        stay = nights(requirements)
        lines.append(
            CostLine(
                label="Hotel",
                amount=hotel_cost,
                detail=f"{hotel.name}, {hotel.price_per_night:,.0f} × {stay} nights",
            )
        )
    elif not hotels:
        notes.append("No hotel prices were found.")

    daily = [day.estimated_cost for day in (itinerary.days if itinerary else [])]
    planned = sum(cost for cost in daily if cost)

    if planned:
        lines.append(
            CostLine(
                label="Food, activities & local transport",
                amount=planned,
                detail=f"planner's estimate over {len(daily)} days",
            )
        )

    total = sum(line.amount for line in lines)
    budget = requirements.budget_amount
    remaining = budget - total if budget is not None else None

    return CostBreakdown(
        currency=currency,
        lines=lines,
        total=total,
        budget=budget,
        remaining=remaining,
        over_budget=remaining is not None and remaining < 0,
        notes=notes,
    )
