# In-memory ring buffer of recent estimate requests, shown on the API screen.
# Estimates are request/response (Appendix A rules out persistence), so a small
# process-local log is enough — no database.
class RequestLog
  MAX_ENTRIES = 25
  @entries = []

  class << self
    def record(entry)
      @entries.unshift entry
      @entries = @entries.first(MAX_ENTRIES)
      entry
    end

    def recent
      @entries
    end

    def clear
      @entries = []
    end
  end
end
