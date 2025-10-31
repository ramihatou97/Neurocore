# Testing Best Practices
**Quick Reference Guide for Frontend Testing**

---

## Table of Contents
1. [Testing MUI Components](#testing-mui-components)
2. [Async Testing Patterns](#async-testing-patterns)
3. [User Interaction Testing](#user-interaction-testing)
4. [Mock Management](#mock-management)
5. [Common Pitfalls](#common-pitfalls)
6. [Debugging Tips](#debugging-tips)

---

## Testing MUI Components

### Dialog Components

#### ✅ Correct Pattern
```javascript
it('should open dialog when button clicked', async () => {
  const user = userEvent.setup({ delay: null })
  renderComponent()

  // Wait for dialog to render
  await user.click(screen.getByRole('button', { name: /Open/i }))

  // Use findBy* for async elements
  const dialog = await screen.findByRole('dialog')
  expect(dialog).toBeInTheDocument()

  // Query dialog content
  const title = await screen.findByText('Dialog Title')
  expect(title).toBeInTheDocument()
})
```

#### ❌ Common Mistakes
```javascript
// WRONG: Immediate query after click
await user.click(screen.getByRole('button', { name: /Open/i }))
expect(screen.getByRole('dialog')).toBeInTheDocument() // Fails!

// WRONG: getByText for async content
expect(screen.getByText('Dialog Title')).toBeInTheDocument() // Fails!
```

### Accordion Components

#### ✅ Correct Pattern
```javascript
it('should display content after expanding accordion', async () => {
  const user = userEvent.setup({ delay: null })
  renderComponent()

  // Expand accordion FIRST
  const accordion = await screen.findByText('Advanced Options')
  await user.click(accordion)

  // THEN query content
  const checkbox = await screen.findByRole('checkbox', { name: /Option/i })
  expect(checkbox).toBeInTheDocument()
})
```

#### ❌ Common Mistakes
```javascript
// WRONG: Query collapsed content
renderComponent()
const checkbox = screen.getByRole('checkbox', { name: /Option/i }) // Not visible!
```

### Select/Dropdown Components

#### ✅ Correct Pattern
```javascript
it('should select option from dropdown', async () => {
  const user = userEvent.setup({ delay: null })
  renderComponent()

  // Find and click select
  const select = await screen.findByRole('combobox', { name: /Format/i })
  await user.click(select)

  // Wait for options to appear
  const option = await screen.findByRole('option', { name: /PDF/i })
  await user.click(option)

  expect(select).toHaveValue('pdf')
})
```

---

## Async Testing Patterns

### Using findBy* Queries

#### ✅ Correct Pattern
```javascript
it('should load data and display it', async () => {
  axios.get.mockResolvedValue({ data: { items: mockItems } })

  renderComponent()

  // findBy* automatically waits (default 1000ms)
  const item = await screen.findByText('Item 1')
  expect(item).toBeInTheDocument()
})
```

### Using waitFor

#### ✅ Correct Pattern
```javascript
it('should update state after API call', async () => {
  const user = userEvent.setup({ delay: null })
  axios.post.mockResolvedValue({ data: { success: true } })

  renderComponent()

  await user.click(screen.getByRole('button', { name: /Submit/i }))

  // Wait for async state updates
  await waitFor(() => {
    expect(screen.getByText('Success!')).toBeInTheDocument()
  })
})
```

#### With Custom Timeout
```javascript
// For slow operations
await waitFor(() => {
  expect(screen.getByText('Completed')).toBeInTheDocument()
}, { timeout: 5000 }) // 5 seconds
```

### Auto-Close Functionality

#### ✅ Correct Pattern
```javascript
it('should auto-close after 2 seconds', async () => {
  renderComponent()

  // Component should be visible initially
  expect(screen.getByText('Alert Message')).toBeInTheDocument()

  // Wait for auto-close (use real timers)
  await waitFor(() => {
    expect(screen.queryByText('Alert Message')).not.toBeInTheDocument()
  }, { timeout: 3000 }) // Buffer for 2-second auto-close
})
```

#### ❌ Common Mistakes
```javascript
// WRONG: Using fake timers with auto-close
vi.useFakeTimers()
renderComponent()
vi.advanceTimersByTime(2000) // Causes race conditions!
```

---

## User Interaction Testing

### Click Events

#### ✅ Correct Pattern
```javascript
it('should handle button click', async () => {
  const user = userEvent.setup({ delay: null })
  const mockOnClick = vi.fn()

  render(<Button onClick={mockOnClick}>Click Me</Button>)

  await user.click(screen.getByRole('button', { name: /Click Me/i }))

  expect(mockOnClick).toHaveBeenCalledTimes(1)
})
```

### Typing in Inputs

#### ✅ Correct Pattern
```javascript
it('should update input value', async () => {
  const user = userEvent.setup({ delay: null })
  renderComponent()

  const input = screen.getByRole('textbox', { name: /Username/i })

  await user.clear(input)
  await user.type(input, 'john.doe@example.com')

  expect(input).toHaveValue('john.doe@example.com')
})
```

### Checkbox/Radio Interactions

#### ✅ Correct Pattern
```javascript
it('should toggle checkbox', async () => {
  const user = userEvent.setup({ delay: null })
  renderComponent()

  const checkbox = screen.getByRole('checkbox', { name: /Accept Terms/i })

  // Initially unchecked
  expect(checkbox).not.toBeChecked()

  // Click to check
  await user.click(checkbox)
  expect(checkbox).toBeChecked()

  // Click to uncheck
  await user.click(checkbox)
  expect(checkbox).not.toBeChecked()
})
```

---

## Mock Management

### Axios Mocking

#### ✅ Correct Pattern
```javascript
// In beforeEach
beforeEach(() => {
  vi.clearAllMocks()
  localStorage.setItem('access_token', 'mock-token')
})

// In test
it('should fetch data with auth', async () => {
  axios.get.mockResolvedValue({ data: { items: [] } })

  renderComponent()

  await waitFor(() => {
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/items'),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer mock-token'
        })
      })
    )
  })
})
```

### Multiple Mock Responses

#### ✅ Correct Pattern
```javascript
it('should handle multiple API calls', async () => {
  axios.get.mockImplementation((url) => {
    if (url.includes('/users')) {
      return Promise.resolve({ data: { users: mockUsers } })
    }
    if (url.includes('/settings')) {
      return Promise.resolve({ data: { settings: mockSettings } })
    }
    return Promise.reject(new Error('Unknown URL'))
  })

  renderComponent()

  await waitFor(() => {
    expect(screen.getByText('User 1')).toBeInTheDocument()
    expect(screen.getByText('Dark Mode')).toBeInTheDocument()
  })
})
```

### DOM API Mocking

#### ✅ Correct Pattern
```javascript
it('should create download link', async () => {
  const user = userEvent.setup({ delay: null })
  axios.post.mockResolvedValue({ data: new Blob(['test']) })

  // Render component FIRST
  renderComponent()

  const exportButton = await screen.findByRole('button', { name: /Export/i })

  // Mock DOM APIs AFTER rendering
  const mockLink = {
    href: '',
    setAttribute: vi.fn(),
    click: vi.fn(),
    remove: vi.fn()
  }
  const spy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

  await user.click(exportButton)

  await waitFor(() => {
    expect(mockLink.click).toHaveBeenCalled()
  })

  // Clean up
  spy.mockRestore()
})
```

#### ❌ Common Mistakes
```javascript
// WRONG: Mock BEFORE rendering
const spy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink)
renderComponent() // React can't create elements!

// WRONG: Forgetting to restore
const spy = vi.spyOn(document, 'createElement').mockReturnValue(mockLink)
// ... test code ...
// Missing: spy.mockRestore() - breaks subsequent tests!
```

---

## Common Pitfalls

### 1. Multiple Elements with Same Text

#### ❌ Problem
```javascript
// Fails when multiple elements have "Collections" text
expect(screen.getByText('Collections')).toBeInTheDocument()
// Error: Found multiple elements with text: Collections
```

#### ✅ Solution
```javascript
// Use getAllByText
const collections = screen.getAllByText('Collections')
expect(collections.length).toBeGreaterThan(0)

// OR use more specific query
expect(screen.getByRole('tab', { name: /Collections/i })).toBeInTheDocument()
```

### 2. Querying Before Render Complete

#### ❌ Problem
```javascript
renderComponent()
const button = screen.getByRole('button', { name: /Submit/i }) // Might not exist yet!
```

#### ✅ Solution
```javascript
renderComponent()
const button = await screen.findByRole('button', { name: /Submit/i })
// OR
await waitFor(() => {
  expect(screen.getByRole('button', { name: /Submit/i })).toBeInTheDocument()
})
```

### 3. Not Cleaning Up Mocks

#### ❌ Problem
```javascript
it('test 1', () => {
  document.createElement = vi.fn(() => mockElement)
  // ... test ...
  // Missing cleanup!
})

it('test 2', () => {
  renderComponent() // Fails! createElement is still mocked
})
```

#### ✅ Solution
```javascript
it('test 1', () => {
  const spy = vi.spyOn(document, 'createElement').mockReturnValue(mockElement)
  // ... test ...
  spy.mockRestore() // Always restore!
})
```

### 4. Testing Implementation Details

#### ❌ Problem
```javascript
// Testing internal state
expect(wrapper.state('isLoading')).toBe(true)

// Testing class names
expect(button.className).toContain('primary-button')
```

#### ✅ Solution
```javascript
// Test user-visible behavior
expect(screen.getByRole('progressbar')).toBeInTheDocument()

// Test accessibility
expect(button).toHaveAttribute('aria-label', 'Submit form')
```

---

## Debugging Tips

### 1. See What's Rendered

```javascript
import { screen } from '@testing-library/react'

it('debug test', () => {
  renderComponent()

  // Print entire DOM
  screen.debug()

  // Print specific element
  screen.debug(screen.getByRole('button'))

  // Print with more lines
  screen.debug(undefined, 30000)
})
```

### 2. Find Available Queries

```javascript
import { logRoles } from '@testing-library/react'

it('find roles', () => {
  const { container } = renderComponent()

  // See all available role queries
  logRoles(container)
})
```

### 3. Check Accessibility Tree

```javascript
it('check accessibility', () => {
  renderComponent()

  // This shows what screen readers "see"
  console.log(screen.getByRole('button', { name: /Submit/i }))
})
```

### 4. Wait for Async Updates

```javascript
it('debug async', async () => {
  renderComponent()

  // See what's rendered now
  screen.debug()

  // Wait for something
  await screen.findByText('Loaded')

  // See what's rendered after
  screen.debug()
})
```

### 5. Check Mock Calls

```javascript
it('debug mocks', async () => {
  axios.get.mockResolvedValue({ data: { items: [] } })

  renderComponent()

  await waitFor(() => {
    console.log('Mock was called:', axios.get.mock.calls.length)
    console.log('With arguments:', axios.get.mock.calls[0])
  })
})
```

---

## Quick Reference: Query Priority

Use this priority when selecting queries:

1. **getByRole** - Preferred (accessibility)
   ```javascript
   screen.getByRole('button', { name: /Submit/i })
   ```

2. **getByLabelText** - Form elements
   ```javascript
   screen.getByLabelText(/Username/i)
   ```

3. **getByPlaceholderText** - Input placeholders
   ```javascript
   screen.getByPlaceholderText(/Enter email/i)
   ```

4. **getByText** - Non-interactive elements
   ```javascript
   screen.getByText(/Welcome/i)
   ```

5. **getByTestId** - Last resort
   ```javascript
   screen.getByTestId('custom-element')
   ```

### Async Variants
- `findBy*` - Returns promise (waits up to 1000ms)
- `getBy*` - Immediate (throws if not found)
- `queryBy*` - Returns null if not found (use with `not.toBeInTheDocument()`)

---

## Common Test Patterns

### Loading States

```javascript
it('should show loading state', async () => {
  axios.get.mockImplementation(() => new Promise(() => {})) // Never resolves

  renderComponent()

  expect(screen.getByRole('progressbar')).toBeInTheDocument()
  expect(screen.getByText(/Loading.../i)).toBeInTheDocument()
})
```

### Error States

```javascript
it('should show error message', async () => {
  axios.get.mockRejectedValue({
    response: { data: { detail: 'Network error' } }
  })

  renderComponent()

  await waitFor(() => {
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })
})
```

### Empty States

```javascript
it('should show empty state', async () => {
  axios.get.mockResolvedValue({ data: { items: [] } })

  renderComponent()

  await waitFor(() => {
    expect(screen.getByText(/No items found/i)).toBeInTheDocument()
  })
})
```

### Form Submission

```javascript
it('should submit form with validation', async () => {
  const user = userEvent.setup({ delay: null })
  const mockOnSubmit = vi.fn()

  render(<Form onSubmit={mockOnSubmit} />)

  // Fill form
  await user.type(screen.getByLabelText(/Email/i), 'test@example.com')
  await user.type(screen.getByLabelText(/Password/i), 'password123')

  // Submit
  await user.click(screen.getByRole('button', { name: /Submit/i }))

  // Verify submission
  await waitFor(() => {
    expect(mockOnSubmit).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123'
    })
  })
})
```

---

## Resources

- [Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [Vitest Docs](https://vitest.dev/)
- [Common Testing Mistakes](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [Test Coverage Report](./TEST_COVERAGE_REPORT.md)

---

**Remember**: Test user behavior, not implementation details!
