from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.cart import CartQuote, CartQuoteRequest
from app.schemas.common import ApiResponse
from app.services import pricing_service

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.post(
    "/quote",
    response_model=ApiResponse[CartQuote],
    summary="Price a cart (works for guests)",
    description=(
        "The cart itself lives on the device. Send its items here to get live prices, stock problems, "
        "voucher discount, delivery options and the exact total the order will charge."
    ),
)
async def quote_cart(payload: CartQuoteRequest, db: DbSession):
    priced = await pricing_service.price_cart(
        db,
        payload.items,
        voucher_code=payload.voucher_code,
        delivery_type=payload.delivery_type,
        city=payload.city,
    )
    return ApiResponse(data=priced.quote)
