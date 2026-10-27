import logging
import time

logger = logging.getLogger("FalconAI.Executor")


class Executor:
    def __init__(self, channel_player=None, channel_ai=None):
        self.channel_player = channel_player
        self.channel_ai = channel_ai

    def execute_action(self, route_name: str, result: dict) -> dict:
        start_time = time.time()
        action_status = "success"
        details = {}

        try:
            if route_name == "video_stream":
                logger.info(f"[Executor] video_stream → passing through: {result.get('data', {}).get('name', '?')}")
                details["route"] = "video_stream"

            elif route_name == "channel_list":
                logger.info("[Executor] channel_list → passing through")
                details["route"] = "channel_list"

            elif route_name in ("channel", "watch_movie") and self.channel_player:
                channel_name = (
                    result.get("data", {}).get("channel")
                    or result.get("data", {}).get("title")
                )
                if channel_name:
                    logger.info(f"[Executor] ChannelPlayer scan for '{channel_name}'")
                    playback_res = self.channel_player.play(channel_name)
                    details["playback"] = playback_res

                    if isinstance(playback_res, dict) and playback_res.get("type") == "video_stream":
                        result = playback_res

            elif route_name == "channel_ai" and self.channel_ai:
                logger.info("[Executor] ChannelAI live frame analysis")
                analysis_res = self.channel_ai.scan_active_feed()
                details["analysis"] = analysis_res

            else:
                logger.info(f"[Executor] Standard pass-through for route '{route_name}'")
                details["route"] = route_name

        except Exception as e:
            logger.error(f"[Executor] Critical failure: {e}")
            action_status = "failed"
            details["error"] = str(e)

        latency = round(time.time() - start_time, 4)

        return {
            "status": action_status,
            "latency": latency,
            "details": details,
            "response": result
        }