// No package declaration — types live at top level.

import java.util.Map;

public class Top {
    public int x;

    public Top(int x) {
        this.x = x;
    }
}

class Helper {
    static Map<String, Integer> counts;
}
