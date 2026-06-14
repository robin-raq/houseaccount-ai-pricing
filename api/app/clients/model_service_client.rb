require "net/http"

# Thin HTTP client for the internal Python model service. Rails owns the public
# contract; the model service owns features -> model -> intervals -> confidence.
class ModelServiceClient
  class Error < StandardError; end

  TIMEOUT_SECONDS = 1.8
  DEFAULT_URL = "http://localhost:8000".freeze

  def self.predict(payload)
    new.predict payload
  end

  def initialize(base_url: ENV["MODEL_SERVICE_URL"].presence || DEFAULT_URL)
    @base_url = base_url
  end

  def self.meta
    new.meta
  end

  def predict(payload)
    response = post "/predict", payload
    raise Error, "model service responded #{response.code}" unless response.code.to_i == 200

    JSON.parse response.body
  end

  def meta
    response = get "/meta"
    raise Error, "model service responded #{response.code}" unless response.code.to_i == 200

    JSON.parse response.body
  end

private

  def get(path)
    uri = URI.join @base_url, path
    http = Net::HTTP.new uri.host, uri.port
    http.use_ssl = uri.scheme == "https"
    http.open_timeout = TIMEOUT_SECONDS
    http.read_timeout = TIMEOUT_SECONDS
    http.get uri
  end

  def post(path, payload)
    uri = URI.join @base_url, path
    http = Net::HTTP.new uri.host, uri.port
    http.use_ssl = uri.scheme == "https"
    http.open_timeout = TIMEOUT_SECONDS
    http.read_timeout = TIMEOUT_SECONDS
    request = Net::HTTP::Post.new uri
    request["Content-Type"] = "application/json"
    request.body = payload.to_json
    http.request request
  end
end
