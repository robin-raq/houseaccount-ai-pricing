require "net/http"

# Posts a produced estimate into HouseAccount's booking-create staging endpoint
# (the outbound "end-to-end" direction). Best-effort: when no staging URL/token is
# configured it returns "skipped", and any failure is reported, never raised — the
# estimate response must not depend on the booking flow being reachable.
class StagingClient
  TIMEOUT_SECONDS = 1.0

  def self.post_estimate(payload, estimate)
    new.post_estimate payload, estimate
  end

  def initialize(url: ENV["STAGING_BOOKINGS_URL"].presence, token: ENV["STAGING_BOOKINGS_TOKEN"])
    @url = url
    @token = token
  end

  def post_estimate(payload, estimate)
    return "skipped" if @url.blank?

    response = post booking_body(payload, estimate)
    response.code.to_i.between?(200, 299) ? "posted" : "error #{response.code}"
  rescue StandardError => error
    "error #{error.class}"
  end

private

  def booking_body(payload, estimate)
    {
      job_id: payload["job_id"],
      service_category: payload["service_category"],
      zip_code: payload["zip_code"],
      estimate_midpoint: estimate["estimate_midpoint"],
      confidence: estimate["confidence"]
    }
  end

  def post(body)
    uri = URI @url
    http = Net::HTTP.new uri.host, uri.port
    http.use_ssl = uri.scheme == "https"
    http.open_timeout = TIMEOUT_SECONDS
    http.read_timeout = TIMEOUT_SECONDS
    request = Net::HTTP::Post.new uri
    request["Content-Type"] = "application/json"
    request["Authorization"] = "Bearer #{@token}" if @token.present?
    request.body = body.to_json
    http.request request
  end
end
