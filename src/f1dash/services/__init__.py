from f1dash.config import settings
from f1dash.services.cache_service import CacheService
from f1dash.services.export_service import ExportService
from f1dash.services.precompute_service import PrecomputeService
from f1dash.services.session_service import SessionService

cache_service = CacheService(redis_url=settings.redis_url)

session_service = SessionService(
	cache_dir=str(settings.fastf1_cache_path),
	snapshot_dir=str(settings.snapshot_path),
	cache_service=cache_service,
	cache_ttl_seconds=settings.cache_ttl_seconds,
)

precompute_service = PrecomputeService(session_service=session_service)
export_service = ExportService(
	session_service=session_service,
	export_dir=str(settings.export_path),
)
