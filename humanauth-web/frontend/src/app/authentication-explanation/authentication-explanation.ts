import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-authentication-explanation',
  imports: [CommonModule, RouterLink],
  templateUrl: './authentication-explanation.html',
  styleUrl: './authentication-explanation.scss',
})
export class AuthenticationExplanation {
  // No special functionality needed for this component
}
