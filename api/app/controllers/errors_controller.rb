# Returns the contract's 405 JSON body for non-POST requests to /pricing-estimate.
class ErrorsController < ApplicationController
  def method_not_allowed
    render_error "Method not allowed", :method_not_allowed
  end
end
