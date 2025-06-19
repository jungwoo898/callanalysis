INSERT INTO audio_properties (
    file_path,
    file_name,
    duration,
    sample_rate,
    channels,
    file_size,
    format,
    created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'));
