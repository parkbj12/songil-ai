"""
MongoDB 연동 모듈
데이터 저장 및 조회 기능
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime
from typing import List, Dict, Optional
import config
import json


class MongoDBManager:
    """MongoDB 데이터베이스 관리 클래스"""
    
    def __init__(self, uri: str = None, db_name: str = None):
        """
        Args:
            uri: MongoDB 연결 URI
            db_name: 데이터베이스 이름
        """
        self.uri = uri or config.MONGODB_URI
        self.db_name = db_name or config.DB_NAME
        self.client = None
        self.db = None
        self.collection = None
        
    def connect(self):
        """MongoDB 연결"""
        try:
            self.client = MongoClient(self.uri)
            # 연결 테스트
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.collection = self.db[config.COLLECTION_NAME]
            print(f"MongoDB 연결 성공: {self.db_name}.{config.COLLECTION_NAME}")
        except ConnectionFailure as e:
            print(f"MongoDB 연결 실패: {e}")
            raise
    
    def disconnect(self):
        """MongoDB 연결 종료"""
        if self.client:
            self.client.close()
            print("MongoDB 연결 종료")
    
    def save_sensor_log(self, user_id: str, date: str, 
                       sensor_data: List[Dict], 
                       anomaly_score: float = None,
                       anomaly_detected: bool = False,
                       chatbot_feedback: str = None) -> str:
        """
        센서 로그 데이터 저장
        
        Args:
            user_id: 사용자 ID
            date: 날짜 (YYYY-MM-DD)
            sensor_data: 센서 데이터 리스트 [{"time": "09:00", "heart_rate": 72, ...}, ...]
            anomaly_score: 이상 점수
            anomaly_detected: 이상 탐지 여부
            chatbot_feedback: 챗봇 피드백
            
        Returns:
            저장된 문서의 _id
        """
        document = {
            "user_id": user_id,
            "date": date,
            "sensor_data": sensor_data,
            "timestamp": datetime.now(),
            "anomaly_score": anomaly_score,
            "anomaly_detected": anomaly_detected,
            "chatbot_feedback": chatbot_feedback
        }
        
        result = self.collection.insert_one(document)
        print(f"센서 로그 저장 완료: user_id={user_id}, date={date}, _id={result.inserted_id}")
        return str(result.inserted_id)
    
    def get_user_data(self, user_id: str, 
                     date: Optional[str] = None,
                     limit: int = 100) -> List[Dict]:
        """
        사용자 데이터 조회
        
        Args:
            user_id: 사용자 ID
            date: 날짜 필터 (None이면 전체)
            limit: 조회 개수 제한
            
        Returns:
            사용자 데이터 리스트
        """
        query = {"user_id": user_id}
        if date:
            query["date"] = date
        
        cursor = self.collection.find(query).sort("timestamp", -1).limit(limit)
        results = list(cursor)
        
        # ObjectId를 문자열로 변환
        for doc in results:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc:
                doc["timestamp"] = doc["timestamp"].isoformat()
        
        print(f"사용자 데이터 조회 완료: user_id={user_id}, {len(results)}개 문서")
        return results
    
    def get_user_anomalies(self, user_id: str, 
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> List[Dict]:
        """
        특정 사용자의 이상 탐지 기록 조회
        
        Args:
            user_id: 사용자 ID
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            이상 탐지 기록 리스트
        """
        query = {
            "user_id": user_id,
            "anomaly_detected": True
        }
        
        if start_date and end_date:
            query["date"] = {"$gte": start_date, "$lte": end_date}
        elif start_date:
            query["date"] = {"$gte": start_date}
        elif end_date:
            query["date"] = {"$lte": end_date}
        
        cursor = self.collection.find(query).sort("timestamp", -1)
        results = list(cursor)
        
        for doc in results:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc:
                doc["timestamp"] = doc["timestamp"].isoformat()
        
        print(f"이상 탐지 기록 조회 완료: user_id={user_id}, {len(results)}개 문서")
        return results
    
    def update_user_anomaly(self, document_id: str,
                           anomaly_score: float,
                           anomaly_detected: bool,
                           chatbot_feedback: str):
        """
        기존 문서의 이상 탐지 정보 업데이트
        
        Args:
            document_id: 문서 _id
            anomaly_score: 이상 점수
            anomaly_detected: 이상 탐지 여부
            chatbot_feedback: 챗봇 피드백
        """
        from bson import ObjectId
        
        update_data = {
            "anomaly_score": anomaly_score,
            "anomaly_detected": anomaly_detected,
            "chatbot_feedback": chatbot_feedback,
            "updated_at": datetime.now()
        }
        
        result = self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_data}
        )
        
        print(f"문서 업데이트 완료: _id={document_id}, 수정된 문서 수: {result.modified_count}")
        return result.modified_count
    
    def get_statistics(self, user_id: str) -> Dict:
        """
        사용자 통계 정보 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            통계 정보 딕셔너리
        """
        total_logs = self.collection.count_documents({"user_id": user_id})
        anomaly_count = self.collection.count_documents({
            "user_id": user_id,
            "anomaly_detected": True
        })
        
        # 평균 이상 점수
        pipeline = [
            {"$match": {"user_id": user_id, "anomaly_score": {"$ne": None}}},
            {"$group": {
                "_id": None,
                "avg_anomaly_score": {"$avg": "$anomaly_score"},
                "max_anomaly_score": {"$max": "$anomaly_score"},
                "min_anomaly_score": {"$min": "$anomaly_score"}
            }}
        ]
        
        stats_result = list(self.collection.aggregate(pipeline))
        stats = stats_result[0] if stats_result else {}
        
        statistics = {
            "user_id": user_id,
            "total_logs": total_logs,
            "anomaly_count": anomaly_count,
            "anomaly_rate": anomaly_count / total_logs if total_logs > 0 else 0,
            "avg_anomaly_score": stats.get("avg_anomaly_score", 0),
            "max_anomaly_score": stats.get("max_anomaly_score", 0),
            "min_anomaly_score": stats.get("min_anomaly_score", 0)
        }
        
        return statistics
    
    def save_notification(self, user_id: str, notification_type: str, 
                         message: str, status: str = "pending") -> str:
        """
        알림 저장
        
        Args:
            user_id: 사용자 ID
            notification_type: 알림 타입 ("health_check", "no_response" 등)
            message: 알림 메시지
            status: 알림 상태 ("pending", "read", "responded")
            
        Returns:
            저장된 문서의 _id
        """
        notification_collection = self.db.get_collection("notifications")
        document = {
            "user_id": user_id,
            "notification_type": notification_type,
            "message": message,
            "status": status,
            "created_at": datetime.now(),
            "read_at": None,
            "responded_at": None
        }
        
        result = notification_collection.insert_one(document)
        print(f"알림 저장 완료: user_id={user_id}, type={notification_type}, _id={result.inserted_id}")
        return str(result.inserted_id)
    
    def get_pending_notifications(self, user_id: str) -> List[Dict]:
        """대기 중인 알림 조회"""
        notification_collection = self.db.get_collection("notifications")
        query = {
            "user_id": user_id,
            "status": "pending",
            "notification_type": {"$in": ["health_check", "no_response_chatbot"]}  # 챗봇에 표시할 알림만
        }
        
        cursor = notification_collection.find(query).sort("created_at", -1)
        results = list(cursor)
        
        for doc in results:
            doc["_id"] = str(doc["_id"])
            if "created_at" in doc:
                doc["created_at"] = doc["created_at"].isoformat()
            if "read_at" in doc and doc["read_at"]:
                doc["read_at"] = doc["read_at"].isoformat()
            if "responded_at" in doc and doc["responded_at"]:
                doc["responded_at"] = doc["responded_at"].isoformat()
        
        return results
    
    def mark_notification_read(self, notification_id: str):
        """알림을 읽음으로 표시"""
        from bson import ObjectId
        notification_collection = self.db.get_collection("notifications")
        
        result = notification_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {
                "$set": {
                    "status": "read",
                    "read_at": datetime.now()
                }
            }
        )
        
        return result.modified_count
    
    def mark_notification_responded(self, notification_id: str):
        """알림에 응답했다고 표시"""
        from bson import ObjectId
        notification_collection = self.db.get_collection("notifications")
        
        result = notification_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {
                "$set": {
                    "status": "responded",
                    "responded_at": datetime.now()
                }
            }
        )
        
        return result.modified_count
    
    def create_indexes(self):
        """인덱스 생성 (성능 최적화)"""
        # user_id와 date에 복합 인덱스
        self.collection.create_index([("user_id", 1), ("date", 1)])
        # timestamp에 인덱스
        self.collection.create_index([("timestamp", -1)])
        # anomaly_detected에 인덱스
        self.collection.create_index([("anomaly_detected", 1)])
        
        # 알림 컬렉션 인덱스
        notification_collection = self.db.get_collection("notifications")
        notification_collection.create_index([("user_id", 1), ("status", 1)])
        notification_collection.create_index([("created_at", -1)])
        
        # 사용자 설정 컬렉션 인덱스
        settings_collection = self.db.get_collection("user_settings")
        settings_collection.create_index([("user_id", 1)], unique=True)
        
        print("인덱스 생성 완료")
    
    def save_user_settings(self, user_id: str, email: str = None, emergency_contacts: List[Dict] = None) -> bool:
        """
        사용자 설정 저장 (이메일, 긴급 연락망)
        
        Args:
            user_id: 사용자 ID
            email: 이메일 주소 (선택)
            emergency_contacts: 긴급 연락망 리스트 (선택)
            
        Returns:
            저장 성공 여부
        """
        settings_collection = self.db.get_collection("user_settings")
        
        try:
            update_data = {}
            if email is not None:
                update_data["email"] = email
            if emergency_contacts is not None:
                update_data["emergency_contacts"] = emergency_contacts
            
            if not update_data:
                return False
            
            update_data["updated_at"] = datetime.now()
            
            result = settings_collection.update_one(
                {"user_id": user_id},
                {"$set": update_data},
                upsert=True
            )
            
            print(f"사용자 설정 저장 완료: user_id={user_id}")
            return True
        except Exception as e:
            print(f"사용자 설정 저장 실패: {e}")
            return False
    
    def get_user_settings(self, user_id: str) -> Dict:
        """
        사용자 설정 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            사용자 설정 딕셔너리 (email, emergency_contacts)
        """
        settings_collection = self.db.get_collection("user_settings")
        
        try:
            settings = settings_collection.find_one({"user_id": user_id})
            
            if settings:
                # _id 제거
                settings.pop("_id", None)
                return settings
            else:
                return {"user_id": user_id, "email": "", "emergency_contacts": []}
        except Exception as e:
            print(f"사용자 설정 조회 실패: {e}")
            return {"user_id": user_id, "email": "", "emergency_contacts": []}
    
    def delete_user_data(self, document_id: str) -> bool:
        """
        사용자 데이터 삭제
        
        Args:
            document_id: 삭제할 문서의 _id
            
        Returns:
            삭제 성공 여부
        """
        from bson import ObjectId
        from bson.errors import InvalidId
        
        try:
            result = self.collection.delete_one({"_id": ObjectId(document_id)})
            if result.deleted_count > 0:
                print(f"데이터 삭제 완료: _id={document_id}")
                return True
            else:
                print(f"삭제할 데이터를 찾을 수 없습니다: _id={document_id}")
                return False
        except InvalidId:
            print(f"잘못된 문서 ID 형식: {document_id}")
            return False
        except Exception as e:
            print(f"데이터 삭제 실패: {e}")
            return False

