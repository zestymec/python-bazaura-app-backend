from typing import List, Optional

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, Pagination
from app.models.custom_request import CustomRequest
from app.schemas.common import ApiResponse
from app.schemas.custom_request import CustomRequestCancel, CustomRequestCreate, CustomRequestOut, QuoteOut
from app.services import custom_request_service

router = APIRouter(prefix="/custom-requests", tags=["Custom requests & gifts"])


def to_out(request: CustomRequest) -> CustomRequestOut:
    data = CustomRequestOut.model_validate(request, from_attributes=True)
    if request.quote:
        data.quote = QuoteOut.model_validate(request.quote)
    return data


@router.post(
    "",
    response_model=ApiResponse[CustomRequestOut],
    status_code=status.HTTP_201_CREATED,
    summary="Ask Bazaura to arrange an item or send a gift",
)
async def create_request(payload: CustomRequestCreate, user: CurrentUser, db: DbSession):
    request = await custom_request_service.create_request(db, user, payload)
    return ApiResponse(message="Request received. We will send you a quote soon.", data=to_out(request))


@router.get("", response_model=ApiResponse[List[CustomRequestOut]], summary="My requests")
async def list_my_requests(user: CurrentUser, db: DbSession, pagination: Pagination):
    requests = await custom_request_service.list_requests(
        db, user=user, offset=pagination.offset, limit=pagination.limit
    )
    return ApiResponse(data=[to_out(r) for r in requests])


@router.get("/{request_id}", response_model=ApiResponse[CustomRequestOut], summary="Request detail")
async def get_my_request(request_id: str, user: CurrentUser, db: DbSession):
    return ApiResponse(data=to_out(await custom_request_service.get_request(db, request_id, user=user)))


@router.post(
    "/{request_id}/accept-quote",
    response_model=ApiResponse[CustomRequestOut],
    summary="Accept the quote; creates a Cash on Delivery order",
)
async def accept_quote(request_id: str, user: CurrentUser, db: DbSession):
    request = await custom_request_service.accept_quote(db, user, request_id)
    return ApiResponse(message="Quote accepted. Your order has been created.", data=to_out(request))


@router.post("/{request_id}/cancel", response_model=ApiResponse[CustomRequestOut], summary="Cancel a request")
async def cancel_request(
    request_id: str, user: CurrentUser, db: DbSession, payload: Optional[CustomRequestCancel] = None
):
    request = await custom_request_service.cancel_request(db, user, request_id, payload.reason if payload else None)
    return ApiResponse(message="Request cancelled", data=to_out(request))
