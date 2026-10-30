  initial begin
    cpu_req_valid = 0; cpu_req_addr = 0; cpu_req_write = 0;
    cpu_req_hit = 0; cpu_req_line_state = MESI_I;
    cpu_resp_ready = 0; dir_req_ready = 0;
    grant_valid = 0; grant_opcode = GRANT_DATA_S; grant_txn_id = 0;
    grant_data_valid = 0; grant_data_txn_id = 0;
    grant_data_beat_idx = 0; grant_data = 0; grant_data_last = 0;
    refill_ready = 0; grant_commit_ready = 0;
    snoop_valid = 0; snoop_line_addr = 0; snoop_opcode = SNOOP_READ;
    snoop_txn_id = 0; snoop_tag_hit = 0; snoop_line_state = MESI_I;
    snoop_rsp_ready = 0; snoop_line_rd_ready = 0;
    snoop_line_rd_hit = 1;
    snoop_array_data_valid = 0; snoop_array_beat_idx = 0;
    snoop_array_data = 0; snoop_array_last = 0; snoop_data_ready = 0;
    cpu_meta_write_ready = 0; snoop_meta_write_ready = 0;
    repeat (3) tick();
    @(negedge clock); reset = 0;

`include "include/cold_refill_and_local_write.svh"

`include "include/remote_owner_and_upgrade.svh"
`include "include/snoop_cases.svh"

`include "include/reset_and_protocol_error_cases.svh"
