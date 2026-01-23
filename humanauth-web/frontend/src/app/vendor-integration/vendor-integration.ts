import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-vendor-integration',
  imports: [CommonModule, RouterLink],
  templateUrl: './vendor-integration.html',
  styleUrl: './vendor-integration.scss',
})
export class VendorIntegration {
  // No special functionality needed for this component
}
