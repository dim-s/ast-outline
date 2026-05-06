# Mix of valid + invalid — adapter should partial-recover on the
# valid bits and surface non-zero error_count for the broken bit.
class Healthy
  def works
  end
end

class Broken
  def good_method
  end

  def bad_method(
end

class StillHealthy
  def also_works
  end
end
