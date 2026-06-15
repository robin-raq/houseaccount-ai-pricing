require "net/http"

# Thin HTTP client for the internal Python model service. Rails owns the public
# contract; the model service owns features -> model -> intervals -> confidence.
class ModelServiceClient
  class Error < StandardError; end

  # A novel request makes a live (cached) LLM call inside the model service, so the
  # read timeout is generous; cached requests return in well under a second.
  OPEN_TIMEOUT = 3
  READ_TIMEOUT = 8
  DEFAULT_URL = "http://localhost:8000".freeze

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
    parse request_json("/predict") { |request| request.body = payload.to_json }
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
    request = verb.new uri
    request["Content-Type"] = "application/json"
    yield request if block_given?
    http.request request
  rescue Net::OpenTimeout, Net::ReadTimeout, SocketError, SystemCallError, IOError => error
    raise Error, "model service unreachable (#{error.class})"
  end

  def parse(response)
    raise Error, "model service responded #{response.code}" unless response.code.to_i == 200

    JSON.parse response.body
  end
end
