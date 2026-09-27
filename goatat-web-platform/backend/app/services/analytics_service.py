"""Analytics service — generates dashboard statistics and chart data."""
from datetime import datetime, timedelta
from typing import Optional
import random
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.profile import Alert
from app.core.logging import logger


class AnalyticsService:
    async def get_dashboard_stats(self, db: AsyncSession) -> dict:
        try:
            total = await db.scalar(select(func.count(Analysis.id)))
            authentic = await db.scalar(
                select(func.count(Analysis.id)).where(Analysis.verdict == "authentic")
            )
            synthetic = await db.scalar(
                select(func.count(Analysis.id)).where(Analysis.verdict == "synthetic")
            )
            inconclusive = await db.scalar(
                select(func.count(Analysis.id)).where(Analysis.verdict == "inconclusive")
            )
            alerts_count = await db.scalar(
                select(func.count(Alert.id)).where(
                    Alert.acknowledged == False, Alert.dismissed == False
                )
            )

            recent_result = await db.execute(
                select(Analysis).order_by(Analysis.created_at.desc()).limit(5)
            )
            recent = recent_result.scalars().all()

            return {
                "total_analyses": total or 0,
                "authentic_count": authentic or 0,
                "synthetic_count": synthetic or 0,
                "inconclusive_count": inconclusive or 0,
                "detection_rate": None,  # Only set when real evaluation data exists
                "recent_analyses": recent,
                "suspicious_alerts": alerts_count or 0,
                "is_demo_data": True,
            }
        except Exception as e:
            logger.error(f"Erreur statistiques dashboard: {e}")
            return self._empty_stats()

    def _empty_stats(self) -> dict:
        return {
            "total_analyses": 0,
            "authentic_count": 0,
            "synthetic_count": 0,
            "inconclusive_count": 0,
            "detection_rate": None,
            "recent_analyses": [],
            "suspicious_alerts": 0,
            "is_demo_data": True,
        }

    async def get_analytics_data(self, db: AsyncSession, days: int = 30) -> dict:
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Daily counts from DB
            result = await db.execute(
                select(
                    func.date(Analysis.created_at).label("date"),
                    func.count(Analysis.id).label("count"),
                    Analysis.verdict,
                )
                .where(Analysis.created_at >= start_date)
                .group_by(func.date(Analysis.created_at), Analysis.verdict)
                .order_by(func.date(Analysis.created_at))
            )
            rows = result.fetchall()

            # Build daily counts
            daily_map: dict[str, dict] = {}
            for row in rows:
                date_str = str(row.date)
                if date_str not in daily_map:
                    daily_map[date_str] = {"date": date_str, "authentic": 0, "synthetic": 0, "inconclusive": 0}
                daily_map[date_str][row.verdict] = row.count

            daily_counts = list(daily_map.values())

            # Verdict distribution
            total = await db.scalar(select(func.count(Analysis.id)))
            authentic = await db.scalar(select(func.count(Analysis.id)).where(Analysis.verdict == "authentic"))
            synthetic = await db.scalar(select(func.count(Analysis.id)).where(Analysis.verdict == "synthetic"))
            inconclusive = await db.scalar(select(func.count(Analysis.id)).where(Analysis.verdict == "inconclusive"))

            # Avg latency
            avg_latency = await db.scalar(select(func.avg(Analysis.inference_time_ms)))

            return {
                "daily_counts": daily_counts,
                "verdict_distribution": {
                    "authentic": authentic or 0,
                    "synthetic": synthetic or 0,
                    "inconclusive": inconclusive or 0,
                },
                "inference_latency_avg_ms": round(avg_latency or 0, 2),
                "score_distribution": [],
                "is_demo_data": (total or 0) == 0,
            }
        except Exception as e:
            logger.error(f"Erreur données analytics: {e}")
            return {
                "daily_counts": [],
                "verdict_distribution": {"authentic": 0, "synthetic": 0, "inconclusive": 0},
                "inference_latency_avg_ms": 0,
                "score_distribution": [],
                "is_demo_data": True,
            }


analytics_service = AnalyticsService()
