import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavBar as NavBarComponent } from './shared/nav-bar/nav-bar';
import { Footer as FooterComponent } from './shared/footer/footer';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, NavBarComponent, FooterComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = signal('HumanAuth Web');
}
