import psutil
import time
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class PerformanceMetrics:
    """성능 메트릭 데이터 클래스"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    disk_usage_percent: float
    gpu_memory_percent: Optional[float] = None
    gpu_memory_used_gb: Optional[float] = None


class PerformanceMonitor:
    """
    시스템 성능 모니터링 클래스
    CPU, 메모리, GPU, 디스크 사용량을 추적합니다.
    """
    
    def __init__(self, log_dir: str = "/app/logs", interval: int = 30):
        """
        성능 모니터 초기화
        
        Parameters
        ----------
        log_dir : str
            로그 디렉토리 경로
        interval : int
            모니터링 간격 (초)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.interval = interval
        self.monitoring = False
        self.monitor_thread = None
        self.metrics_history = []
        
        # GPU 사용 가능 여부 확인
        self.gpu_available = self._check_gpu_availability()
        
        self._start_time = None
        
    def _check_gpu_availability(self) -> bool:
        """GPU 사용 가능 여부를 확인합니다."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """현재 시스템 메트릭을 수집합니다."""
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 사용률
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        
        # 디스크 사용률
        disk = psutil.disk_usage('/')
        disk_usage_percent = disk.percent
        
        # GPU 메트릭 (사용 가능한 경우)
        gpu_memory_percent = None
        gpu_memory_used_gb = None
        
        if self.gpu_available:
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.memory_stats()
                    gpu_memory_used_gb = gpu_memory.get('allocated_bytes.all.current', 0) / (1024**3)
                    gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                    gpu_memory_percent = (gpu_memory_used_gb / gpu_memory_total) * 100
            except Exception as e:
                print(f"GPU 메트릭 수집 실패: {e}")
        
        return PerformanceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            disk_usage_percent=disk_usage_percent,
            gpu_memory_percent=gpu_memory_percent,
            gpu_memory_used_gb=gpu_memory_used_gb
        )
    
    def start_monitoring(self):
        """성능 모니터링을 시작합니다."""
        if self.monitoring:
            print("모니터링이 이미 실행 중입니다.")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"성능 모니터링 시작 (간격: {self.interval}초)")
    
    def stop_monitoring(self):
        """성능 모니터링을 중지합니다."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("성능 모니터링 중지")
    
    def _monitor_loop(self):
        """모니터링 루프"""
        while self.monitoring:
            try:
                metrics = self.get_current_metrics()
                self.metrics_history.append(metrics)
                
                # 로그 파일에 저장
                self._save_metrics(metrics)
                
                # 메모리 사용량이 높으면 경고
                if metrics.memory_percent > 80:
                    print(f"⚠️ 메모리 사용량 높음: {metrics.memory_percent:.1f}%")
                
                if metrics.gpu_memory_percent and metrics.gpu_memory_percent > 80:
                    print(f"⚠️ GPU 메모리 사용량 높음: {metrics.gpu_memory_percent:.1f}%")
                
                time.sleep(self.interval)
                
            except Exception as e:
                print(f"모니터링 오류: {e}")
                time.sleep(self.interval)
    
    def _save_metrics(self, metrics: PerformanceMetrics):
        """메트릭을 로그 파일에 저장합니다."""
        log_file = self.log_dir / f"performance_{time.strftime('%Y%m%d')}.log"
        
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cpu_percent": round(metrics.cpu_percent, 2),
            "memory_percent": round(metrics.memory_percent, 2),
            "memory_used_gb": round(metrics.memory_used_gb, 2),
            "disk_usage_percent": round(metrics.disk_usage_percent, 2),
            "gpu_memory_percent": round(metrics.gpu_memory_percent, 2) if metrics.gpu_memory_percent else None,
            "gpu_memory_used_gb": round(metrics.gpu_memory_used_gb, 2) if metrics.gpu_memory_used_gb else None
        }
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"메트릭 저장 실패: {e}")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """성능 통계 요약을 반환합니다."""
        if not self.metrics_history:
            return {"message": "수집된 메트릭이 없습니다."}
        
        cpu_values = [m.cpu_percent for m in self.metrics_history]
        memory_values = [m.memory_percent for m in self.metrics_history]
        gpu_values = [m.gpu_memory_percent for m in self.metrics_history if m.gpu_memory_percent]
        
        stats = {
            "total_samples": len(self.metrics_history),
            "cpu": {
                "avg": round(sum(cpu_values) / len(cpu_values), 2),
                "max": round(max(cpu_values), 2),
                "min": round(min(cpu_values), 2)
            },
            "memory": {
                "avg": round(sum(memory_values) / len(memory_values), 2),
                "max": round(max(memory_values), 2),
                "min": round(min(memory_values), 2)
            }
        }
        
        if gpu_values:
            stats["gpu"] = {
                "avg": round(sum(gpu_values) / len(gpu_values), 2),
                "max": round(max(gpu_values), 2),
                "min": round(min(gpu_values), 2)
            }
        
        return stats
    
    def cleanup_old_logs(self, max_days: int = 7):
        """오래된 로그 파일을 정리합니다."""
        current_time = time.time()
        max_age_seconds = max_days * 24 * 3600
        
        for log_file in self.log_dir.glob("performance_*.log"):
            if current_time - log_file.stat().st_mtime > max_age_seconds:
                try:
                    log_file.unlink()
                    print(f"오래된 로그 파일 삭제: {log_file.name}")
                except Exception as e:
                    print(f"로그 파일 삭제 실패: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """시스템 정보를 반환합니다."""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
            "gpu_available": self.gpu_available,
            "platform": psutil.platform(),
            "python_version": psutil.sys.version
        }
    
    def start(self):
        """처리 시간 측정 시작"""
        self._start_time = time.time()
    
    def get_elapsed_time(self) -> float:
        """시작 이후 경과 시간(초) 반환"""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time 