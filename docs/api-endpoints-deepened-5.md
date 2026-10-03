# APEX-OS Deepened API Endpoints — Modules 5

Comprehensive reference for deepened IoT, NLP, Vision, Speech, and Knowledge endpoints.

**Base URL:** `https://api.apex-os.io/v2`
**Auth:** `Authorization: Bearer <token>`
**Content-Type:** `application/json` unless noted

---

## 1. IoT Endpoints

### 1.1 Device Management

#### List Devices
- **Method:** `GET`
- **Path:** `/iot/devices`
- **Query:** `?type=sensor&status=online&page=1&limit=50`
- **Response 200:**
```json
{ "devices": [{ "id": "dev_001", "name": "Temp Sensor A", "type": "sensor", "status": "online", "firmware": "2.1.0", "last_seen": "2026-10-03T10:00:00Z" }], "total": 128, "page": 1 }
```
- **Status:** 200, 401, 403

#### Get Device
- **Method:** `GET`
- **Path:** `/iot/devices/{device_id}`
- **Response 200:**
```json
{ "id": "dev_001", "name": "Temp Sensor A", "type": "sensor", "status": "online", "firmware": "2.1.0", "metadata": { "location": "Building 3" }, "last_seen": "2026-10-03T10:00:00Z" }
```
- **Status:** 200, 401, 404

#### Register Device
- **Method:** `POST`
- **Path:** `/iot/devices`
- **Request:**
```json
{ "name": "Humidity Sensor B", "type": "sensor", "metadata": { "location": "Warehouse" } }
```
- **Response 201:**
```json
{ "id": "dev_002", "name": "Humidity Sensor B", "type": "sensor", "status": "provisioning", "created_at": "2026-10-03T10:05:00Z" }
```
- **Status:** 201, 400, 401, 409

#### Update Device
- **Method:** `PATCH`
- **Path:** `/iot/devices/{device_id}`
- **Request:**
```json
{ "name": "Humidity Sensor B-Updated", "metadata": { "location": "Warehouse-2" } }
```
- **Response 200:**
```json
{ "id": "dev_002", "name": "Humidity Sensor B-Updated", "metadata": { "location": "Warehouse-2" } }
```
- **Status:** 200, 400, 401, 404

#### Delete Device
- **Method:** `DELETE`
- **Path:** `/iot/devices/{device_id}`
- **Response 204:** No content
- **Status:** 204, 401, 404

### 1.2 MQTT

#### Publish Message
- **Method:** `POST`
- **Path:** `/iot/mqtt/publish`
- **Request:**
```json
{ "topic": "sensors/temp/dev_001", "payload": { "temperature": 23.5, "unit": "C" }, "qos": 1, "retain": false }
```
- **Response 200:**
```json
{ "message_id": "msg_abc123", "topic": "sensors/temp/dev_001", "published_at": "2026-10-03T10:10:00Z" }
```
- **Status:** 200, 400, 401, 422

#### Subscribe Topic
- **Method:** `POST`
- **Path:** `/iot/mqtt/subscribe`
- **Request:**
```json
{ "topic": "sensors/temp/+", "qos": 1 }
```
- **Response 200:**
```json
{ "subscription_id": "sub_xyz789", "topic": "sensors/temp/+", "status": "active" }
```
- **Status:** 200, 400, 401

#### Unsubscribe Topic
- **Method:** `DELETE`
- **Path:** `/iot/mqtt/subscribe/{subscription_id}`
- **Response 204:** No content
- **Status:** 204, 401, 404

#### List Subscriptions
- **Method:** `GET`
- **Path:** `/iot/mqtt/subscriptions`
- **Response 200:**
```json
{ "subscriptions": [{ "id": "sub_xyz789", "topic": "sensors/temp/+", "qos": 1, "status": "active" }] }
```
- **Status:** 200, 401

### 1.3 Monitoring

#### Get Device Metrics
- **Method:** `GET`
- **Path:** `/iot/monitoring/devices/{device_id}/metrics`
- **Query:** `?metric=temperature&from=2026-10-01&to=2026-10-03&aggregation=avg`
- **Response 200:**
```json
{ "device_id": "dev_001", "metric": "temperature", "aggregation": "avg", "data_points": [ { "timestamp": "2026-10-01T00:00:00Z", "value": 22.1 }, { "timestamp": "2026-10-02T00:00:00Z", "value": 23.0 } ] }
```
- **Status:** 200, 401, 404

#### Get Fleet Health
- **Method:** `GET`
- **Path:** `/iot/monitoring/fleet/health`
- **Response 200:**
```json
{ "total_devices": 128, "online": 120, "offline": 5, "degraded": 3, "alerts": [{ "device_id": "dev_042", "severity": "warning", "message": "High latency" }] }
```
- **Status:** 200, 401

#### Create Alert Rule
- **Method:** `POST`
- **Path:** `/iot/monitoring/alerts`
- **Request:**
```json
{ "name": "High Temp Alert", "condition": "temperature > 35", "device_filter": { "type": "sensor" }, "severity": "critical", "notification": { "channel": "webhook", "target": "https://hooks.example.com/alert" } }
```
- **Response 201:**
```json
{ "id": "alert_001", "name": "High Temp Alert", "status": "active", "created_at": "2026-10-03T10:15:00Z" }
```
- **Status:** 201, 400, 401

### 1.4 Device Shadow

#### Get Shadow
- **Method:** `GET`
- **Path:** `/iot/shadow/{device_id}`
- **Response 200:**
```json
{ "device_id": "dev_001", "reported": { "firmware": "2.1.0", "temperature": 23.5 }, "desired": { "firmware": "2.2.0" }, "version": 12, "timestamp": "2026-10-03T10:20:00Z" }
```
- **Status:** 200, 401, 404

#### Update Shadow
- **Method:** `PATCH`
- **Path:** `/iot/shadow/{device_id}`
- **Request:**
```json
{ "desired": { "firmware": "2.2.0", "reporting_interval": 60 } }
```
- **Response 200:**
```json
{ "device_id": "dev_001", "desired": { "firmware": "2.2.0", "reporting_interval": 60 }, "version": 13, "timestamp": "2026-10-03T10:25:00Z" }
```
- **Status:** 200, 400, 401, 404

#### Delete Shadow
- **Method:** `DELETE`
- **Path:** `/iot/shadow/{device_id}`
- **Response 204:** No content
- **Status:** 204, 401, 404

### 1.5 OTA

#### Create Firmware Update
- **Method:** `POST`
- **Path:** `/iot/ota/updates`
- **Request:**
```json
{ "firmware_version": "2.2.0", "binary_url": "https://storage.apex-os.io/fw/2.2.0.bin", "target_devices": ["dev_001", "dev_002"], "strategy": "rolling", "rollout_percentage": 10 }
```
- **Response 201:**
```json
{ "id": "ota_001", "firmware_version": "2.2.0", "status": "scheduled", "created_at": "2026-10-03T10:30:00Z" }
```
- **Status:** 201, 400, 401

#### Get Update Status
- **Method:** `GET`
- **Path:** `/iot/ota/updates/{update_id}`
- **Response 200:**
```json
{ "id": "ota_001", "firmware_version": "2.2.0", "status": "in_progress", "progress": 45, "target_count": 2, "success_count": 1, "failure_count": 0 }
```
- **Status:** 200, 401, 404

#### Cancel Update
- **Method:** `POST`
- **Path:** `/iot/ota/updates/{update_id}/cancel`
- **Response 200:**
```json
{ "id": "ota_001", "status": "cancelled", "cancelled_at": "2026-10-03T10:35:00Z" }
```
- **Status:** 200, 401, 404, 409

---

## 2. NLP Endpoints

### 2.1 Named Entity Recognition (NER)

#### Extract Entities
- **Method:** `POST`
- **Path:** `/nlp/ner`
- **Request:**
```json
{ "text": "Apple Inc. was founded by Steve Jobs in Cupertino on April 1, 1976.", "language": "en", "model": "default" }
```
- **Response 200:**
```json
{ "entities": [ { "text": "Apple Inc.", "label": "ORG", "start": 0, "end": 10, "confidence": 0.98 }, { "text": "Steve Jobs", "label": "PERSON", "start": 29, "end": 39, "confidence": 0.97 }, { "text": "Cupertino", "label": "GPE", "start": 43, "end": 52, "confidence": 0.95 }, { "text": "April 1, 1976", "label": "DATE", "start": 56, "end": 69, "confidence": 0.96 } ] }
```
- **Status:** 200, 400, 401, 413

### 2.2 Sentiment Analysis

#### Analyze Sentiment
- **Method:** `POST`
- **Path:** `/nlp/sentiment`
- **Request:**
```json
{ "text": "The product exceeded my expectations. Absolutely fantastic!", "language": "en", "granularity": "document" }
```
- **Response 200:**
```json
{ "sentiment": "positive", "score": 0.92, "confidence": 0.95, "aspects": [] }
```
- **Status:** 200, 400, 401

#### Aspect-Based Sentiment
- **Method:** `POST`
- **Path:** `/nlp/sentiment/aspects`
- **Request:**
```json
{ "text": "The battery life is great but the screen is dim.", "aspects": ["battery life", "screen"] }
```
- **Response 200:**
```json
{ "aspects": [ { "aspect": "battery life", "sentiment": "positive", "score": 0.85 }, { "aspect": "screen", "sentiment": "negative", "score": -0.65 } ] }
```
- **Status:** 200, 400, 401

### 2.3 Text Classification

#### Classify Text
- **Method:** `POST`
- **Path:** `/nlp/classify`
- **Request:**
```json
{ "text": "Breaking: New AI model achieves state-of-the-art results.", "categories": ["technology", "sports", "politics", "entertainment"], "multi_label": false }
```
- **Response 200:**
```json
{ "classifications": [ { "label": "technology", "score": 0.94 } ] }
```
- **Status:** 200, 400, 401

### 2.4 Translation

#### Translate Text
- **Method:** `POST`
- **Path:** `/nlp/translate`
- **Request:**
```json
{ "text": "Hello, how are you?", "source_language": "en", "target_language": "es", "formality": "default" }
```
- **Response 200:**
```json
{ "translated_text": "Hola, ¿cómo estás?", "source_language": "en", "target_language": "es", "confidence": 0.98 }
```
- **Status:** 200, 400, 401, 413

#### Batch Translate
- **Method:** `POST`
- **Path:** `/nlp/translate/batch`
- **Request:**
```json
{ "texts": ["Hello", "Goodbye"], "source_language": "en", "target_language": "fr" }
```
- **Response 200:**
```json
{ "translations": [ { "translated_text": "Bonjour" }, { "translated_text": "Au revoir" } ] }
```
- **Status:** 200, 400, 401

### 2.5 Question Answering

#### Answer Question
- **Method:** `POST`
- **Path:** `/nlp/qa`
- **Request:**
```json
{ "question": "What is the capital of France?", "context": "France is a country in Europe. Its capital is Paris.", "max_answer_length": 50 }
```
- **Response 200:**
```json
{ "answer": "Paris", "score": 0.97, "start": 44, "end": 49 }
```
- **Status:** 200, 400, 401

---

## 3. Vision Endpoints

### 3.1 Object Detection

#### Detect Objects
- **Method:** `POST`
- **Path:** `/vision/detect`
- **Content-Type:** `multipart/form-data`
- **Request:** `image: <binary>, confidence_threshold: 0.5, model: "yolov8"`
- **Response 200:**
```json
{ "objects": [ { "label": "person", "confidence": 0.94, "bbox": [120, 80, 200, 350] }, { "label": "car", "confidence": 0.88, "bbox": [300, 150, 180, 120] } ], "image_size": [640, 480] }
```
- **Status:** 200, 400, 401, 413, 415

### 3.2 Image Classification

#### Classify Image
- **Method:** `POST`
- **Path:** `/vision/classify`
- **Content-Type:** `multipart/form-data`
- **Request:** `image: <binary>, top_k: 3`
- **Response 200:**
```json
{ "classifications": [ { "label": "golden retriever", "score": 0.96 }, { "label": "labrador", "score": 0.03 }, { "label": "dog", "score": 0.01 } ] }
```
- **Status:** 200, 400, 401, 415

### 3.3 Segmentation

#### Segment Image
- **Method:** `POST`
- **Path:** `/vision/segment`
- **Content-Type:** `multipart/form-data`
- **Request:** `image: <binary>, mode: "semantic", return_mask: true`
- **Response 200:**
```json
{ "segments": [ { "label": "person", "area_fraction": 0.35, "mask_url": "https://cdn.apex-os.io/masks/seg_001.png" }, { "label": "sky", "area_fraction": 0.45, "mask_url": "https://cdn.apex-os.io/masks/seg_002.png" } ] }
```
- **Status:** 200, 400, 401, 415

### 3.4 Face Recognition

#### Detect Faces
- **Method:** `POST`
- **Path:** `/vision/faces/detect`
- **Content-Type:** `multipart/form-data`
- **Request:** `image: <binary>, include_landmarks: true, include_attributes: true`
- **Response 200:**
```json
{ "faces": [ { "bbox": [100, 50, 200, 250], "confidence": 0.99, "landmarks": { "left_eye": [130, 120], "right_eye": [170, 120], "nose": [150, 150], "mouth": [150, 180] }, "attributes": { "age": 28, "gender": "female", "emotion": "happy" } } ] }
```
- **Status:** 200, 400, 401, 415

#### Verify Face
- **Method:** `POST`
- **Path:** `/vision/faces/verify`
- **Content-Type:** `multipart/form-data`
- **Request:** `image1: <binary>, image2: <binary>, threshold: 0.6`
- **Response 200:**
```json
{ "match": true, "similarity": 0.87, "threshold": 0.6 }
```
- **Status:** 200, 400, 401, 415

### 3.5 Video Analysis

#### Analyze Video
- **Method:** `POST`
- **Path:** `/vision/video/analyze`
- **Content-Type:** `multipart/form-data`
- **Request:** `video: <binary>, tasks: ["object_tracking", "scene_detection"], sample_rate: 1`
- **Response 202:**
```json
{ "job_id": "vid_job_001", "status": "processing", "estimated_duration": 30 }
```
- **Status:** 202, 400, 401, 415

#### Get Video Analysis Result
- **Method:** `GET`
- **Path:** `/vision/video/analyze/{job_id}`
- **Response 200:**
```json
{ "job_id": "vid_job_001", "status": "completed", "results": { "objects_tracked": [{ "label": "person", "track_id": 1, "frames": [1, 2, 3, 4, 5] }], "scenes": [{ "label": "outdoor", "start_frame": 1, "end_frame": 120 }] } }
```
- **Status:** 200, 401, 404

---

## 4. Speech Endpoints

### 4.1 Automatic Speech Recognition (ASR)

#### Transcribe Audio
- **Method:** `POST`
- **Path:** `/speech/asr`
- **Content-Type:** `multipart/form-data`
- **Request:** `audio: <binary>, language: "en", model: "large-v3", timestamps: true`
- **Response 200:**
```json
{ "text": "Hello, this is a test transcription.", "language": "en", "confidence": 0.96, "segments": [ { "start": 0.0, "end": 1.5, "text": "Hello," }, { "start": 1.5, "end": 4.2, "text": "this is a test transcription." } ] }
```
- **Status:** 200, 400, 401, 415

### 4.2 Text-to-Speech (TTS)

#### Synthesize Speech
- **Method:** `POST`
- **Path:** `/speech/tts`
- **Request:**
```json
{ "text": "Welcome to APEX-OS.", "voice": "en-US-Neural2-F", "speed": 1.0, "pitch": 0, "format": "mp3" }
```
- **Response 200:**
```json
{ "audio_url": "https://cdn.apex-os.io/tts/tts_001.mp3", "duration_seconds": 2.1, "format": "mp3", "sample_rate": 24000 }
```
- **Status:** 200, 400, 401, 413

### 4.3 Speaker Identification

#### Identify Speaker
- **Method:** `POST`
- **Path:** `/speech/speaker/identify`
- **Content-Type:** `multipart/form-data`
- **Request:** `audio: <binary>, candidate_speaker_ids: ["spk_001", "spk_002"]`
- **Response 200:**
```json
{ "identified_speaker": "spk_001", "confidence": 0.89, "scores": [ { "speaker_id": "spk_001", "score": 0.89 }, { "speaker_id": "spk_002", "score": 0.11 } ] }
```
- **Status:** 200, 400, 401, 415

#### Enroll Speaker
- **Method:** `POST`
- **Path:** `/speech/speaker/enroll`
- **Content-Type:** `multipart/form-data`
- **Request:** `audio: <binary>, speaker_id: "spk_003", metadata: { "name": "John Doe" }`
- **Response 201:**
```json
{ "speaker_id": "spk_003", "status": "enrolled", "voiceprint_id": "vp_003" }
```
- **Status:** 201, 400, 401, 415

### 4.4 Emotion Recognition

#### Detect Emotion
- **Method:** `POST`
- **Path:** `/speech/emotion`
- **Content-Type:** `multipart/form-data`
- **Request:** `audio: <binary>, granularity: "utterance"`
- **Response 200:**
```json
{ "emotion": "happy", "confidence": 0.88, "scores": { "happy": 0.88, "neutral": 0.08, "sad": 0.02, "angry": 0.01, "fearful": 0.01 } }
```
- **Status:** 200, 400, 401, 415

### 4.5 Transcription (Long-Form)

#### Transcribe Long Audio
- **Method:** `POST`
- **Path:** `/speech/transcribe`
- **Content-Type:** `multipart/form-data`
- **Request:** `audio: <binary>, language: "en", diarization: true, num_speakers: 2`
- **Response 202:**
```json
{ "job_id": "tr_job_001", "status": "processing", "estimated_duration": 120 }
```
- **Status:** 202, 400, 401, 415

#### Get Transcription Result
- **Method:** `GET`
- **Path:** `/speech/transcribe/{job_id}`
- **Response 200:**
```json
{ "job_id": "tr_job_001", "status": "completed", "text": "Full transcript here...", "speakers": [ { "speaker_id": 1, "segments": [{ "start": 0.0, "end": 5.2, "text": "Hello everyone." }] }, { "speaker_id": 2, "segments": [{ "start": 5.5, "end": 10.1, "text": "Hi, thanks for joining." }] } ] }
```
- **Status:** 200, 401, 404

---

## 5. Knowledge Endpoints

### 5.1 Knowledge Graph

#### Create Graph
- **Method:** `POST`
- **Path:** `/knowledge/graphs`
- **Request:**
```json
{ "name": "Product KG", "description": "Product knowledge graph", "schema": { "node_types": ["Product", "Category", "Feature"], "edge_types": ["HAS_FEATURE", "BELONGS_TO"] } }
```
- **Response 201:**
```json
{ "id": "kg_001", "name": "Product KG", "status": "active", "created_at": "2026-10-03T11:00:00Z" }
```
- **Status:** 201, 400, 401

#### Add Triples
- **Method:** `POST`
- **Path:** `/knowledge/graphs/{graph_id}/triples`
- **Request:**
```json
{ "triples": [ { "subject": "ProductA", "predicate": "HAS_FEATURE", "object": "Wireless" }, { "subject": "ProductA", "predicate": "BELONGS_TO", "object": "Electronics" } ] }
```
- **Response 201:**
```json
{ "added": 2, "graph_version": 3 }
```
- **Status:** 201, 400, 401, 404

#### Query Graph
- **Method:** `POST`
- **Path:** `/knowledge/graphs/{graph_id}/query`
- **Request:**
```json
{ "query": "MATCH (p:Product)-[:HAS_FEATURE]->(f:Feature) WHERE f.name = 'Wireless' RETURN p.name", "language": "cypher" }
```
- **Response 200:**
```json
{ "results": [ { "p.name": "ProductA" }, { "p.name": "ProductB" } ] }
```
- **Status:** 200, 400, 401, 404

### 5.2 Ontology

#### Create Ontology
- **Method:** `POST`
- **Path:** `/knowledge/ontologies`
- **Request:**
```json
{ "name": "E-Commerce Ontology", "classes": [{ "name": "Product", "properties": [{ "name": "price", "type": "float" }, { "name": "name", "type": "string" }] }], "relationships": [{ "name": "isSubClassOf", "domain": "Product", "range": "Item" }] }
```
- **Response 201:**
```json
{ "id": "ont_001", "name": "E-Commerce Ontology", "status": "active" }
```
- **Status:** 201, 400, 401

#### Validate Ontology
- **Method:** `POST`
- **Path:** `/knowledge/ontologies/{ontology_id}/validate`
- **Response 200:**
```json
{ "valid": true, "warnings": [], "errors": [] }
```
- **Status:** 200, 401, 404

### 5.3 Reasoning

#### Run Inference
- **Method:** `POST`
- **Path:** `/knowledge/reasoning/infer`
- **Request:**
```json
{ "graph_id": "kg_001", "rules": [ { "name": "transitive_feature", "body": "MATCH (a)-[:HAS_FEATURE]->(f)<-[:HAS_FEATURE]-(b) CREATE (a)-[:SIMILAR_TO]->(b)" } ], "max_iterations": 5 }
```
- **Response 200:**
```json
{ "inferred_triples": [ { "subject": "ProductA", "predicate": "SIMILAR_TO", "object": "ProductB" } ], "iterations_run": 3 }
```
- **Status:** 200, 400, 401, 404

### 5.4 Semantic Search

#### Semantic Search
- **Method:** `POST`
- **Path:** `/knowledge/search`
- **Request:**
```json
{ "query": "wireless headphones with noise cancellation", "graph_id": "kg_001", "top_k": 5, "score_threshold": 0.7 }
```
- **Response 200:**
```json
{ "results": [ { "node_id": "prod_042", "label": "ProductA", "score": 0.91, "matched_properties": { "features": ["Wireless", "Noise Cancellation"] } }, { "node_id": "prod_055", "label": "ProductB", "score": 0.84, "matched_properties": { "features": ["Wireless"] } } ] }
```
- **Status:** 200, 400, 401, 404

### 5.5 Knowledge Extraction

#### Extract Knowledge
- **Method:** `POST`
- **Path:** `/knowledge/extract`
- **Request:**
```json
{ "text": "The Tesla Model 3 is an electric vehicle with a range of 358 miles and autopilot features.", "extract": ["entities", "relations", "attributes"], "target_graph_id": "kg_001" }
```
- **Response 200:**
```json
{ "entities": [ { "text": "Tesla Model 3", "type": "Product" }, { "text": "electric vehicle", "type": "Category" } ], "relations": [ { "subject": "Tesla Model 3", "predicate": "IS_A", "object": "electric vehicle" } ], "attributes": [ { "entity": "Tesla Model 3", "name": "range", "value": "358 miles" }, { "entity": "Tesla Model 3", "name": "features", "value": "autopilot" } ] }
```
- **Status:** 200, 400, 401, 413

---

## Error Response Format

All errors return:
```json
{ "error": { "code": "RESOURCE_NOT_FOUND", "message": "The requested resource was not found.", "details": null } }
```

| Status | Meaning |
|--------|---------|
| 400 | Bad Request — invalid parameters |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource does not exist |
| 409 | Conflict — resource already exists or state conflict |
| 413 | Payload Too Large — request body exceeds limit |
| 415 | Unsupported Media Type — wrong content type |
| 422 | Unprocessable Entity — semantic validation failed |
| 429 | Too Many Requests — rate limit exceeded |
| 500 | Internal Server Error |
