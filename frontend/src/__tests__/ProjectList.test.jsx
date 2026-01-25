import "@testing-library/jest-dom/vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import ProjectList from "../components/ProjectList";
import { setupMsw } from "../test/setupTests";

const noop = () => {};

describe("ProjectList", () => {
  setupMsw();

  test("creates a project and shows it in the list", async () => {
    const user = userEvent.setup();
    const theme = createTheme({
      components: {
        MuiButtonBase: {
          defaultProps: {
            disableRipple: true,
          },
        },
      },
    });
    await act(async () => {
      render(
        <ThemeProvider theme={theme}>
          <ProjectList
            onProjectSelect={noop}
            onSetCurrentProject={noop}
            onNavigate={noop}
          />
        </ThemeProvider>
      );
    });

    // Wait for initial empty state
    await screen.findByText(/No projects yet/i);

    // Open dialog
    await act(async () => {
      await user.click(screen.getByRole("button", { name: /new project/i }));
    });

    const nameInput = await screen.findByLabelText(/project name/i);
    await act(async () => {
      await user.type(nameInput, "My Project");
    });

    await act(async () => {
      await user.click(screen.getByRole("button", { name: /create/i }));
    });

    // Newly created project card should appear
    await waitFor(() => {
      expect(screen.getByText("My Project")).toBeTruthy();
    });
  });
});

