def get_index_progres_key(job_id: str):
    return f"index_progress_{job_id}"

def get_index_status_key(job_id: str):
    return f"index_status_{job_id}"

def get_cluster_status_key(job_id: str):
    return f"cluster_status_{job_id}"

def get_index_progress_channel(job_id: str):
    return f"index_progress_channel_{job_id}"

def get_cluster_status_channel(job_id: str):
    return f"cluster_status_channel_{job_id}"
