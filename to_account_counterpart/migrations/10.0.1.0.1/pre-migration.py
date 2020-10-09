
def migrate(cr, version):
    cr.execute("""
        ALTER TABLE account_move_line_ctp DROP CONSTRAINT IF EXISTS account_move_line_ctp_check_max_countered_amt;
    """)

