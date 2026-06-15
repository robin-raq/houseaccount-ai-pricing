require "net/http"
require "openssl"

# Posts a produced estimate into HouseAccount's booking-create staging endpoint
# (POST /api/bookings) as the outbound "end-to-end" direction. Authentication is
# HouseAccount's signed-request scheme: App-Name, App-Timestamp, and an App-Signature
# that is HMAC-SHA256(secret, "<timestamp>.<body>"). Best-effort: with no URL/secret
# configured it returns "skipped", and any failure is reported, never raised — the
# estimate response must not depend on the booking flow being reachable.
class StagingClient
  TIMEOUT_SECONDS = 2.0
  DEMO_PHONE = "5555550100".freeze # the pricing request is anonymized; booking needs a phone

  def self.post_estimate(payload, estimate)
    new.post_estimate payload, estimate
  end

  def initialize(
    url: ENV["STAGING_BOOKINGS_URL"].presence,
    app_name: ENV["STAGING_APP_NAME"],
    secret: ENV["STAGING_SIGNING_SECRET"]
  )
    @url = url
    @app_name = app_name
    @secret = secret
  end

  def post_estimate(payload, estimate)
    return "skipped" if @url.blank? || @secret.blank?

    response = post booking_body(payload, estimate).to_json
    response.code.to_i.between?(200, 299) ? "posted" : "error #{response.code}"
  rescue StandardError => error
    "error #{error.class}"
  end

private

  def booking_body(payload, estimate)
    {
      name: "Pricing demo #{payload["job_id"]}",
      zip: payload["zip_code"],
      phone: DEMO_PHONE,
      summary: payload["job_description"].to_s[0, 200],
      deadline: payload["deadline"],
      estimate: { min: estimate["estimate_lo"].to_i, max: estimate["estimate_hi"].to_i }
    }.compact
  end

  def post(body)
    uri = URI @url
    timestamp = Time.now.to_i.to_s
    request = Net::HTTP::Post.new uri
    request["Content-Type"] = "application/json"
    request["App-Name"] = @app_name
    request["App-Timestamp"] = timestamp
    request["App-Signature"] = sign timestamp, body
    request.body = body
    connection(uri).request request
  end

  def sign(timestamp, body)
    OpenSSL::HMAC.hexdigest "SHA256", @secret.to_s, "#{timestamp}.#{body}"
  end

  def connection(uri)
    http = Net::HTTP.new uri.host, uri.port
    http.use_ssl = uri.scheme == "https"
    http.open_timeout = TIMEOUT_SECONDS
    http.read_timeout = TIMEOUT_SECONDS
    http
  end
end
