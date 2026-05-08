import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vite-plus/test";

afterEach(cleanup);

import { LinkedTitle } from "./linked-title";

describe("LinkedTitle", () => {
  describe("renders as link when showLinkInTitle and website.url are provided", () => {
    it("renders an anchor tag", () => {
      render(
        <LinkedTitle title="Acme Corp" website={{ url: "https://acme.com", label: "Acme" }} showLinkInTitle={true} />,
      );

      const link = screen.getByRole("link", { name: "Acme Corp" });
      expect(link).toBeDefined();
      expect(link.getAttribute("href")).toBe("https://acme.com");
    });

    it("sets target=_blank and rel=noopener on the link", () => {
      render(
        <LinkedTitle title="Company" website={{ url: "https://example.com", label: "" }} showLinkInTitle={true} />,
      );

      const link = screen.getByRole("link");
      expect(link.getAttribute("target")).toBe("_blank");
      expect(link.getAttribute("rel")).toBe("noopener");
    });

    it("wraps the title in a strong tag inside the link", () => {
      render(
        <LinkedTitle title="Bold Title" website={{ url: "https://example.com", label: "" }} showLinkInTitle={true} />,
      );

      const strong = screen.getByText("Bold Title");
      expect(strong.tagName).toBe("STRONG");
    });
  });

  describe("renders as plain strong tag otherwise", () => {
    it("renders strong when showLinkInTitle is false", () => {
      render(
        <LinkedTitle title="Plain Title" website={{ url: "https://example.com", label: "" }} showLinkInTitle={false} />,
      );

      const strong = screen.getByText("Plain Title");
      expect(strong.tagName).toBe("STRONG");
      expect(screen.queryByRole("link")).toBeNull();
    });

    it("renders strong when showLinkInTitle is undefined", () => {
      render(<LinkedTitle title="No Link" />);

      expect(screen.getByText("No Link").tagName).toBe("STRONG");
      expect(screen.queryByRole("link")).toBeNull();
    });

    it("renders strong when website is undefined", () => {
      render(<LinkedTitle title="No Website" showLinkInTitle={true} />);

      expect(screen.getByText("No Website").tagName).toBe("STRONG");
      expect(screen.queryByRole("link")).toBeNull();
    });

    it("renders strong when website.url is empty", () => {
      render(<LinkedTitle title="Empty URL" website={{ url: "", label: "" }} showLinkInTitle={true} />);

      expect(screen.getByText("Empty URL").tagName).toBe("STRONG");
      expect(screen.queryByRole("link")).toBeNull();
    });
  });

  describe("className prop", () => {
    it("applies className to the link element", () => {
      render(
        <LinkedTitle
          title="Styled"
          website={{ url: "https://x.com", label: "" }}
          showLinkInTitle={true}
          className="custom-class"
        />,
      );

      const link = screen.getByRole("link");
      expect(link.className).toContain("custom-class");
    });

    it("applies className to the strong element", () => {
      render(<LinkedTitle title="Styled Strong" className="my-class" />);

      const strong = screen.getByText("Styled Strong");
      expect(strong.className).toContain("my-class");
    });
  });
});
