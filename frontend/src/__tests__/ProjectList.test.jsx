import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProjectList from "../components/ProjectList";

const noop = () => {};

describe("ProjectList", () => {
  test("creates a project and shows it in the list", async () => {
    render(
      <ProjectList
        onProjectSelect={noop}
        onSetCurrentProject={noop}
        onNavigate={noop}
      />
    );

    // Wait for initial empty state
    await screen.findByText(/No projects yet/i);

    // Open dialog
    await userEvent.click(screen.getByRole("button", { name: /new project/i }));

    const nameInput = await screen.findByLabelText(/project name/i);
    await userEvent.type(nameInput, "My Project");

    await userEvent.click(screen.getByRole("button", { name: /create/i }));

    // Newly created project card should appear
    await waitFor(() =>
      expect(screen.getByText("My Project")).toBeInTheDocument()
    );
  });
});

