require "net/http"

# Thin HTTP client for the internal Python model service. Rails owns the public
# contract; the model service owns features -> model -> intervals -> confidence.
# Any transport error, non-200, malformed body, or incomplete payload is normalized
# to ModelServiceClient::Error so the controllers return a controlled 503, never a 500.
class ModelServiceClient
  class Error < StandardError; end

  # A novel request makes a live (cached) LLM call inside the model service, so the
  # read timeout has headroom; cached requests return in well under a second.
  OPEN_TIMEOUT = 3
  READ_TIMEOUT = 5
  WRITE_TIMEOUT = 3
  DEFAULT_URL = "http://localhost:8000".freeze
  REQUIRED_KEYS = %w[
    job_id estimate_lo estimate_hi estimate_midpoint confidence model_version
  ].freeze

  def self.predict(payload)
    new.predict payload
  end

  def self.meta
    new.meta
  end

  def initialize(base_url: ENV["MODEL_SERVICE_URL"].presence || DEFAULT_URL)
    @base_url = base_url
  end

  def predict(payload)
    estimate = parse request_json("/predict") { |request| request.body = payload.to_json }
    missing = REQUIRED_KEYS.reject { |key| estimate.key? key }
    raise Error, "model service omitted #{missing.join(", ")}" if missing.any?

    estimate
  end

  def meta
    parse request_json("/meta", verb: Net::HTTP::Get)
  end

private

  def request_json(path, verb: Net::HTTP::Post)
    uri = URI.join @base_url, path
    http = Net::HTTP.new uri.host, uri.port
    http.use_ssl = uri.scheme == "https"
    http.open_timeout = OPEN_TIMEOUT
    http.read_timeout = READ_TIMEOUT
    http.write_timeout = WRITE_TIMEOUT
    request = verb.new uri
    request["Content-Type"] = "application/json"
    yield request if block_given?
    http.request request
  rescue Net::OpenTimeout, Net::ReadTimeout, Net::WriteTimeout,
         SocketError, SystemCallError, IOError => error
    raise Error, "model service unreachable (#{error.class})"
  end

  def parse(response)
    raise Error, "model service responded #{response.code}" unless response.code.to_i == 200

    JSON.parse response.body
  rescue JSON::ParserError
    raise Error, "model service returned malformed JSON"
  end
end
