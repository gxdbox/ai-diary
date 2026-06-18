from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/sentry-error")
async def trigger_sentry_error():
    """
    测试端点:触发一个除零错误,Sentry 应该捕获它
    
    访问此端点后,检查 Sentry Dashboard 是否收到错误报告
    
    注意: 生产环境建议删除或限制此端点访问
    """
    # 这会触发 ZeroDivisionError,Sentry 会自动捕获
    division_by_zero = 1 / 0
    return {"message": "This should never be reached"}
