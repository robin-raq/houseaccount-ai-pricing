# Proxies the model service's metadata (eval numbers, version, category coverage)
# to the demo UI's Evaluation and Model Card screens.
module Demo
  class ModelsController < ApplicationController
    def show
      render json: ModelServiceClient.meta
    rescue ModelServiceClient::Error
      render_error "Model metadata unavailable", :service_unavailable
    end
  end
end
