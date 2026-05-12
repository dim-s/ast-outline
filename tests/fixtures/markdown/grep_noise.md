# Hooks tutorial

The `useState` hook is the bread and butter of React local state.

## Basic usage

Call useState in your component:

```javascript
import { useState } from "react";

function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}
```

That's all there is to useState in its simplest form.

## Edge cases

Don't call useState conditionally — see the rules of hooks.

```python
# Different language, but same word — should still be filtered.
useState = "this is python, not js"
print(useState)
```

End of file. The word useState appears one final time in prose here.

<!--
TODO: revisit useState patterns here once the new compiler ships.
NOTE: hidden draft annotation, should not surface in grep results.
-->

<!-- useState: shorter inline comment, also hidden -->

<div data-tag="useState">Embedded HTML keeps useState searchable here.</div>
