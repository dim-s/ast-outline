# Nested module shape that SHOULD collapse to App::Models::Internal —
# every level holds exactly one named child (excluding comments).
module App
  # outer module rdoc
  module Models
    module Internal
      class Worker
        def run
        end
      end
    end
  end
end
