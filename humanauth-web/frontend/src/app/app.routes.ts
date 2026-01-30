import { Routes } from "@angular/router";
import { HomePage as HomePageComponent } from "./home-page/home-page";
import { DemoSection as DemoSectionComponent } from "./demo-section/demo-section";
import { AuthPageComponent } from "./auth-page/auth-page.component";
import { Architecture as ArchitectureComponent } from "./architecture/architecture";

export const routes: Routes = [
  { path: "", component: HomePageComponent },
  { path: "architecture", component: ArchitectureComponent },
  { path: "demo", component: DemoSectionComponent },
  { path: "auth", component: AuthPageComponent },
  { path: "**", redirectTo: "" }
];
