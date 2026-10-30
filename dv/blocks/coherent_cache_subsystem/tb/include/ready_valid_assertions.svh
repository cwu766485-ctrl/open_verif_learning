  // Ready/valid protocol assertions. These deliberately check the integrated
  // subsystem boundary and both CPU response channels under actual stalls.
  always_ff @(posedge clock) begin : ready_valid_assertions
    if (reset) begin
      stalled_cpu_req_q <= '0;
      stalled_cpu_resp_q <= '0;
      stalled_mmio_req_q <= 1'b0;
      stalled_mmio_resp_q <= 1'b0;
      stalled_mem_rd_req_q <= 1'b0;
      stalled_mem_rd_data_q <= 1'b0;
      stalled_mem_wr_req_q <= 1'b0;
      stalled_mem_wr_data_q <= 1'b0;
      stalled_dir_req_q <= 1'b0;
      stalled_snoop_q <= 1'b0;
      stalled_grant_q <= 1'b0;
      stalled_l2_data_q <= 1'b0;
      stalled_l2_write_q <= 1'b0;
      for (integer core = 0; core < 2; core = core + 1) begin
        cpu_req_addr_hold_q[core] <= '0;
        cpu_req_write_hold_q[core] <= 1'b0;
        cpu_req_wmask_hold_q[core] <= '0;
        cpu_req_wdata_hold_q[core] <= '0;
        cpu_resp_addr_hold_q[core] <= '0;
        cpu_resp_write_hold_q[core] <= 1'b0;
        cpu_resp_rdata_hold_q[core] <= '0;
        cpu_resp_txn_hold_q[core] <= '0;
      end
      mmio_addr_hold_q <= '0;
      mmio_size_hold_q <= '0;
      mmio_write_hold_q <= 1'b0;
      mmio_wmask_hold_q <= '0;
      mmio_wdata_hold_q <= '0;
      mmio_resp_data_hold_q <= '0;
      mem_rd_addr_hold_q <= '0;
      mem_rd_txn_hold_q <= '0;
      mem_rd_data_txn_hold_q <= '0;
      mem_rd_data_beat_hold_q <= '0;
      mem_rd_data_hold_q <= '0;
      mem_rd_data_last_hold_q <= 1'b0;
      mem_rd_data_error_hold_q <= 1'b0;
      mem_wr_addr_hold_q <= '0;
      mem_wr_txn_hold_q <= '0;
      mem_wr_data_txn_hold_q <= '0;
      mem_wr_data_beat_hold_q <= '0;
      mem_wr_data_hold_q <= '0;
      mem_wr_data_last_hold_q <= 1'b0;
      dir_req_src_hold_q <= 1'b0;
      dir_req_opcode_hold_q <= REQ_GETS;
      dir_req_addr_hold_q <= '0;
      dir_req_txn_hold_q <= '0;
      snoop_target_hold_q <= 1'b0;
      snoop_opcode_hold_q <= SNOOP_READ;
      snoop_addr_hold_q <= '0;
      snoop_txn_hold_q <= '0;
      grant_dst_hold_q <= 1'b0;
      grant_opcode_hold_q <= GRANT_DATA_S;
      grant_addr_hold_q <= '0;
      grant_txn_hold_q <= '0;
      l2_data_beat_hold_q <= '0;
      l2_data_hold_q <= '0;
      l2_data_last_hold_q <= 1'b0;
      l2_write_addr_hold_q <= '0;
      l2_write_beat_hold_q <= '0;
      l2_write_data_hold_q <= '0;
      l2_write_last_hold_q <= 1'b0;
    end else begin
      for (integer core = 0; core < 2; core = core + 1) begin
        if (stalled_cpu_req_q[core])
          assert (cpu_req_ready[core] || (cpu_req_valid[core] &&
                  cpu_req_addr[core] == cpu_req_addr_hold_q[core] &&
                  cpu_req_write[core] == cpu_req_write_hold_q[core] &&
                  cpu_req_wmask[core] == cpu_req_wmask_hold_q[core] &&
                  cpu_req_wdata[core] == cpu_req_wdata_hold_q[core]))
            else $fatal(1, "CPU%0d request changed while stalled", core);
        if (stalled_cpu_resp_q[core])
          assert (cpu_resp_ready[core] || (cpu_resp_valid[core] &&
                  cpu_resp_addr[core] == cpu_resp_addr_hold_q[core] &&
                  cpu_resp_write[core] == cpu_resp_write_hold_q[core] &&
                  cpu_resp_rdata[core] == cpu_resp_rdata_hold_q[core] &&
                  cpu_resp_txn_id[core] == cpu_resp_txn_hold_q[core]))
            else $fatal(1, "CPU%0d response changed while stalled: valid=%b/%b addr=%08x/%08x write=%b/%b data=%016x/%016x txn=%0h/%0h",
                        core, cpu_resp_valid[core], stalled_cpu_resp_q[core],
                        cpu_resp_addr[core], cpu_resp_addr_hold_q[core],
                        cpu_resp_write[core], cpu_resp_write_hold_q[core],
                        cpu_resp_rdata[core], cpu_resp_rdata_hold_q[core],
                        cpu_resp_txn_id[core], cpu_resp_txn_hold_q[core]);
        stalled_cpu_req_q[core] <= cpu_req_valid[core] && !cpu_req_ready[core];
        cpu_req_addr_hold_q[core] <= cpu_req_addr[core];
        cpu_req_write_hold_q[core] <= cpu_req_write[core];
        cpu_req_wmask_hold_q[core] <= cpu_req_wmask[core];
        cpu_req_wdata_hold_q[core] <= cpu_req_wdata[core];
        stalled_cpu_resp_q[core] <= cpu_resp_valid[core] && !cpu_resp_ready[core];
        cpu_resp_addr_hold_q[core] <= cpu_resp_addr[core];
        cpu_resp_write_hold_q[core] <= cpu_resp_write[core];
        cpu_resp_rdata_hold_q[core] <= cpu_resp_rdata[core];
        cpu_resp_txn_hold_q[core] <= cpu_resp_txn_id[core];
      end

      if (stalled_mmio_req_q)
        assert (mmio_req_ready || (mmio_req_valid && mmio_req_addr == mmio_addr_hold_q &&
                mmio_req_size == mmio_size_hold_q &&
                mmio_req_write == mmio_write_hold_q &&
                mmio_req_wmask == mmio_wmask_hold_q &&
                mmio_req_wdata == mmio_wdata_hold_q))
          else $fatal(1, "MMIO request changed while stalled");
      if (stalled_mmio_resp_q)
        assert (mmio_resp_ready ||
                (mmio_resp_valid && mmio_resp_rdata == mmio_resp_data_hold_q))
          else $fatal(1, "MMIO response changed while stalled");
      stalled_mmio_req_q <= mmio_req_valid && !mmio_req_ready;
      mmio_addr_hold_q <= mmio_req_addr;
      mmio_size_hold_q <= mmio_req_size;
      mmio_write_hold_q <= mmio_req_write;
      mmio_wmask_hold_q <= mmio_req_wmask;
      mmio_wdata_hold_q <= mmio_req_wdata;
      stalled_mmio_resp_q <= mmio_resp_valid && !mmio_resp_ready;
      mmio_resp_data_hold_q <= mmio_resp_rdata;

      if (stalled_dir_req_q)
        assert (dut.dir_req_ready || (dut.cluster_dir_req_valid &&
                dut.cluster_dir_req_src_id == dir_req_src_hold_q &&
                dut.cluster_dir_req_opcode == dir_req_opcode_hold_q &&
                dut.cluster_dir_req_addr == dir_req_addr_hold_q &&
                dut.cluster_dir_req_txn_id == dir_req_txn_hold_q))
          else $fatal(1, "arbiter request changed while Directory was stalled");
      if (stalled_snoop_q)
        assert (dut.dir_snoop_ready || (dut.dir_snoop_valid && dut.dir_snoop_target == snoop_target_hold_q &&
                dut.dir_snoop_opcode == snoop_opcode_hold_q &&
                dut.dir_snoop_addr == snoop_addr_hold_q &&
                dut.dir_snoop_txn_id == snoop_txn_hold_q))
          else $fatal(1, "Directory snoop changed while L1 was stalled");
      if (stalled_grant_q)
        assert (dut.dir_grant_ready || (dut.dir_grant_valid && dut.dir_grant_dst == grant_dst_hold_q &&
                dut.dir_grant_opcode == grant_opcode_hold_q &&
                dut.dir_grant_addr == grant_addr_hold_q &&
                dut.dir_grant_txn_id == grant_txn_hold_q))
          else $fatal(1, "Directory grant changed while L1 was stalled");
      if (stalled_l2_data_q)
        assert (dut.l2_line_data_ready || (dut.l2_line_data_valid &&
                dut.l2_line_data_beat_idx == l2_data_beat_hold_q &&
                dut.l2_line_data == l2_data_hold_q &&
                dut.l2_line_data_last == l2_data_last_hold_q))
          else $fatal(1, "L2 line data changed while destination was stalled");
      if (stalled_l2_write_q)
        assert (dut.l2_line_wr_ready || (dut.l2_line_wr_valid && dut.l2_line_wr_addr == l2_write_addr_hold_q &&
                dut.l2_line_wr_beat_idx == l2_write_beat_hold_q &&
                dut.l2_line_wr_data == l2_write_data_hold_q &&
                dut.l2_line_wr_last == l2_write_last_hold_q))
          else $fatal(1, "L2 line write changed while array was stalled");
      stalled_dir_req_q <= dut.cluster_dir_req_valid && !dut.dir_req_ready;
      dir_req_src_hold_q <= dut.cluster_dir_req_src_id;
      dir_req_opcode_hold_q <= dut.cluster_dir_req_opcode;
      dir_req_addr_hold_q <= dut.cluster_dir_req_addr;
      dir_req_txn_hold_q <= dut.cluster_dir_req_txn_id;
      stalled_snoop_q <= dut.dir_snoop_valid && !dut.dir_snoop_ready;
      snoop_target_hold_q <= dut.dir_snoop_target;
      snoop_opcode_hold_q <= dut.dir_snoop_opcode;
      snoop_addr_hold_q <= dut.dir_snoop_addr;
      snoop_txn_hold_q <= dut.dir_snoop_txn_id;
      stalled_grant_q <= dut.dir_grant_valid && !dut.dir_grant_ready;
      grant_dst_hold_q <= dut.dir_grant_dst;
      grant_opcode_hold_q <= dut.dir_grant_opcode;
      grant_addr_hold_q <= dut.dir_grant_addr;
      grant_txn_hold_q <= dut.dir_grant_txn_id;
      stalled_l2_data_q <= dut.l2_line_data_valid && !dut.l2_line_data_ready;
      l2_data_beat_hold_q <= dut.l2_line_data_beat_idx;
      l2_data_hold_q <= dut.l2_line_data;
      l2_data_last_hold_q <= dut.l2_line_data_last;
      stalled_l2_write_q <= dut.l2_line_wr_valid && !dut.l2_line_wr_ready;
      l2_write_addr_hold_q <= dut.l2_line_wr_addr;
      l2_write_beat_hold_q <= dut.l2_line_wr_beat_idx;
      l2_write_data_hold_q <= dut.l2_line_wr_data;
      l2_write_last_hold_q <= dut.l2_line_wr_last;

      if (cpu_resp_valid[0] && !cpu_resp_ready[0])
        cover_cpu_resp_stall <= cover_cpu_resp_stall + 1;
      if (mmio_req_valid && !mmio_req_ready)
        cover_mmio_req_stall <= cover_mmio_req_stall + 1;
      if (mmio_resp_valid && !mmio_resp_ready)
        cover_mmio_resp_stall <= cover_mmio_resp_stall + 1;
      if (mem_rd_req_valid && !mem_rd_req_ready)
        cover_mem_rd_req_stall <= cover_mem_rd_req_stall + 1;
      if (dut.mem_fill_writer_active_q && !dut.l2_line_wr_ready)
        cover_l2_fill_stall <= cover_l2_fill_stall + 1;
      if (mem_wr_req_valid && !mem_wr_req_ready)
        cover_mem_wr_req_stall <= cover_mem_wr_req_stall + 1;
      if (mem_wr_data_valid && !mem_wr_data_ready)
        cover_mem_wr_data_stall <= cover_mem_wr_data_stall + 1;
      if (dut.cluster_dir_req_valid && !dut.dir_req_ready)
        cover_dir_req_stall <= cover_dir_req_stall + 1;

      if (stalled_mem_rd_req_q)
        assert (mem_rd_req_ready ||
                (mem_rd_req_valid && mem_rd_req_addr == mem_rd_addr_hold_q &&
                 mem_rd_req_txn_id == mem_rd_txn_hold_q))
          else $fatal(1, "memory read request changed while stalled");
      if (stalled_mem_rd_data_q)
        assert (mem_rd_data_ready ||
                (mem_rd_data_valid && mem_rd_data_txn_id == mem_rd_data_txn_hold_q &&
                 mem_rd_data_beat_idx == mem_rd_data_beat_hold_q &&
                 mem_rd_data == mem_rd_data_hold_q &&
                 mem_rd_data_last == mem_rd_data_last_hold_q &&
                 mem_rd_data_error == mem_rd_data_error_hold_q))
          else $fatal(1, "memory read beat changed while stalled");
      if (stalled_mem_wr_req_q)
        assert (mem_wr_req_ready ||
                (mem_wr_req_valid && mem_wr_req_addr == mem_wr_addr_hold_q &&
                 mem_wr_req_txn_id == mem_wr_txn_hold_q))
          else $fatal(1, "memory write request changed while stalled");
      if (stalled_mem_wr_data_q)
        assert (mem_wr_data_ready ||
                (mem_wr_data_valid && mem_wr_data_txn_id == mem_wr_data_txn_hold_q &&
                 mem_wr_data_beat_idx == mem_wr_data_beat_hold_q &&
                 mem_wr_data == mem_wr_data_hold_q &&
                 mem_wr_data_last == mem_wr_data_last_hold_q))
          else $fatal(1, "memory write beat changed while stalled");
      stalled_mem_rd_req_q <= mem_rd_req_valid && !mem_rd_req_ready;
      mem_rd_addr_hold_q <= mem_rd_req_addr;
      mem_rd_txn_hold_q <= mem_rd_req_txn_id;
      stalled_mem_rd_data_q <= mem_rd_data_valid && !mem_rd_data_ready;
      mem_rd_data_txn_hold_q <= mem_rd_data_txn_id;
      mem_rd_data_beat_hold_q <= mem_rd_data_beat_idx;
      mem_rd_data_hold_q <= mem_rd_data;
      mem_rd_data_last_hold_q <= mem_rd_data_last;
      mem_rd_data_error_hold_q <= mem_rd_data_error;
      stalled_mem_wr_req_q <= mem_wr_req_valid && !mem_wr_req_ready;
      mem_wr_addr_hold_q <= mem_wr_req_addr;
      mem_wr_txn_hold_q <= mem_wr_req_txn_id;
      stalled_mem_wr_data_q <= mem_wr_data_valid && !mem_wr_data_ready;
      mem_wr_data_txn_hold_q <= mem_wr_data_txn_id;
      mem_wr_data_beat_hold_q <= mem_wr_data_beat_idx;
      mem_wr_data_hold_q <= mem_wr_data;
      mem_wr_data_last_hold_q <= mem_wr_data_last;
    end
  end
