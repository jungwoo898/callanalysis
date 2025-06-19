INSERT INTO consultation_analysis (
    audio_properties_id,
    business_type,
    classification_type,
    detail_classification,
    consultation_result,
    summary,
    customer_request,
    solution,
    additional_info,
    confidence,
    processing_time,
    created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now')) 